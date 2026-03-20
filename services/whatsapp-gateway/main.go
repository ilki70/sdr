package main

import (
	"bytes"
	"context"
	"encoding/base64"
	"encoding/json"
	"errors"
	"fmt"
	"log"
	"mime"
	"net/http"
	"net/url"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"
	"unicode"

	qrcode "github.com/skip2/go-qrcode"
	"go.mau.fi/whatsmeow"
	waProto "go.mau.fi/whatsmeow/binary/proto"
	"go.mau.fi/whatsmeow/store/sqlstore"
	"go.mau.fi/whatsmeow/types"
	"go.mau.fi/whatsmeow/types/events"
	waLog "go.mau.fi/whatsmeow/util/log"
	"google.golang.org/protobuf/proto"
	_ "modernc.org/sqlite"
)

type GatewayConfig struct {
	TenantID       string `json:"tenant_id"`
	IntegrationID  string `json:"integration_id"`
	CallbackURL    string `json:"callback_url"`
	CallbackSecret string `json:"callback_secret"`
}

type SessionStatus struct {
	Connected     bool      `json:"connected"`
	SessionStatus string    `json:"session_status"`
	PairedPhone   string    `json:"paired_phone,omitempty"`
	QRCodeDataURL string    `json:"qr_code_data_url,omitempty"`
	QRCodeText    string    `json:"qr_code_text,omitempty"`
	LastEvent     string    `json:"last_event,omitempty"`
	LastError     string    `json:"last_error,omitempty"`
	UpdatedAt     time.Time `json:"updated_at,omitempty"`
}

type InboundPayload struct {
	TenantID      string            `json:"tenant_id"`
	IntegrationID string            `json:"integration_id"`
	ChatID        string            `json:"chat_id"`
	SenderID      string            `json:"sender_id"`
	SenderName    string            `json:"sender_name,omitempty"`
	MessageID     string            `json:"message_id"`
	MessageText   string            `json:"message_text"`
	PushName      string            `json:"push_name,omitempty"`
	SentAt        time.Time         `json:"sent_at,omitempty"`
	Attachments   []MediaAttachment `json:"attachments,omitempty"`
}

type MediaAttachment struct {
	Kind     string `json:"kind"`
	FileRef  string `json:"file_ref"`
	MimeType string `json:"mime_type,omitempty"`
	Caption  string `json:"caption,omitempty"`
	Filename string `json:"filename,omitempty"`
}

type InboundResponse struct {
	Duplicate          bool     `json:"duplicate"`
	LeadID             string   `json:"lead_id"`
	ConversationID     string   `json:"conversation_id"`
	ReplyText          string   `json:"reply_text"`
	ReplyFragments     []string `json:"reply_fragments"`
	FollowUpSuggestion string   `json:"follow_up_suggestion"`
}

type Manager struct {
	mu         sync.RWMutex
	client     *whatsmeow.Client
	config     GatewayConfig
	status     SessionStatus
	dataDir    string
	configPath string
	secret     string
}

func main() {
	port := getenv("WHATSAPP_GATEWAY_PORT", "8090")
	dataDir := getenv("WHATSAPP_GATEWAY_DATA_DIR", "data")
	gatewaySecret := getenv("WHATSAPP_GATEWAY_SECRET", "whatsapp-gateway-local")

	manager, err := NewManager(dataDir, gatewaySecret)
	if err != nil {
		log.Fatalf("failed to start gateway: %v", err)
	}

	mux := http.NewServeMux()
	mux.HandleFunc("/health", manager.handleHealth)
	mux.HandleFunc("/api/v1/session/config", manager.handleSessionConfig)
	mux.HandleFunc("/api/v1/session/connect", manager.handleConnect)
	mux.HandleFunc("/api/v1/session/disconnect", manager.handleDisconnect)
	mux.HandleFunc("/api/v1/session/status", manager.handleStatus)
	mux.HandleFunc("/api/v1/media/", manager.handleMedia)

	server := &http.Server{
		Addr:              ":" + port,
		Handler:           manager.requireSecret(mux),
		ReadHeaderTimeout: 10 * time.Second,
	}

	log.Printf("whatsapp gateway listening on :%s", port)
	if err := server.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
		log.Fatalf("server error: %v", err)
	}
}

func NewManager(dataDir string, gatewaySecret string) (*Manager, error) {
	if err := os.MkdirAll(dataDir, 0o755); err != nil {
		return nil, err
	}
	if err := os.MkdirAll(filepath.Join(dataDir, "media"), 0o755); err != nil {
		return nil, err
	}

	ctx := context.Background()
	sessionDBPath := filepath.ToSlash(filepath.Join(dataDir, "session.db"))
	container, err := sqlstore.New(
		ctx,
		"sqlite",
		fmt.Sprintf(
			"file:%s?_pragma=foreign_keys(1)&_pragma=journal_mode(WAL)&_pragma=synchronous(NORMAL)&_pragma=busy_timeout(5000)",
			sessionDBPath,
		),
		waLog.Stdout("DB", "INFO", true),
	)
	if err != nil {
		return nil, err
	}
	deviceStore, err := container.GetFirstDevice(ctx)
	if err != nil {
		return nil, err
	}

	client := whatsmeow.NewClient(deviceStore, waLog.Stdout("Client", "INFO", true))
	manager := &Manager{
		client:     client,
		dataDir:    dataDir,
		configPath: filepath.Join(dataDir, "runtime.json"),
		secret:     gatewaySecret,
		status: SessionStatus{
			SessionStatus: "idle",
			UpdatedAt:     time.Now().UTC(),
		},
	}

	if err := manager.loadConfig(); err != nil {
		return nil, err
	}
	client.AddEventHandler(manager.handleEvent)
	if client.Store.ID != nil {
		manager.status.PairedPhone = client.Store.ID.User
		manager.status.SessionStatus = "stored_session"
	}
	return manager, nil
}

func (m *Manager) loadConfig() error {
	payload, err := os.ReadFile(m.configPath)
	if err != nil {
		if errors.Is(err, os.ErrNotExist) {
			return nil
		}
		return err
	}
	return json.Unmarshal(payload, &m.config)
}

func (m *Manager) saveConfig() error {
	payload, err := json.MarshalIndent(m.config, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(m.configPath, payload, 0o600)
}

func (m *Manager) updateStatus(mutator func(*SessionStatus)) {
	m.mu.Lock()
	defer m.mu.Unlock()
	mutator(&m.status)
	m.status.UpdatedAt = time.Now().UTC()
}

func (m *Manager) snapshotStatus() SessionStatus {
	m.mu.RLock()
	defer m.mu.RUnlock()
	return m.status
}

func (m *Manager) snapshotConfig() GatewayConfig {
	m.mu.RLock()
	defer m.mu.RUnlock()
	return m.config
}

func (m *Manager) requireSecret(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == "/health" {
			next.ServeHTTP(w, r)
			return
		}
		if r.Header.Get("X-WhatsApp-Gateway-Secret") != m.secret {
			writeJSON(w, http.StatusUnauthorized, map[string]string{"message": "invalid gateway secret"})
			return
		}
		next.ServeHTTP(w, r)
	})
}

func (m *Manager) handleHealth(w http.ResponseWriter, _ *http.Request) {
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func (m *Manager) handleSessionConfig(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPut {
		writeJSON(w, http.StatusMethodNotAllowed, map[string]string{"message": "method not allowed"})
		return
	}
	var payload GatewayConfig
	if err := json.NewDecoder(r.Body).Decode(&payload); err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]string{"message": "invalid payload"})
		return
	}
	if payload.TenantID == "" || payload.IntegrationID == "" || payload.CallbackURL == "" || payload.CallbackSecret == "" {
		writeJSON(w, http.StatusBadRequest, map[string]string{"message": "tenant_id, integration_id, callback_url and callback_secret are required"})
		return
	}

	m.mu.Lock()
	m.config = payload
	m.mu.Unlock()
	if err := m.saveConfig(); err != nil {
		writeJSON(w, http.StatusInternalServerError, map[string]string{"message": err.Error()})
		return
	}
	writeJSON(w, http.StatusOK, map[string]string{"status": "configured"})
}

func (m *Manager) handleConnect(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeJSON(w, http.StatusMethodNotAllowed, map[string]string{"message": "method not allowed"})
		return
	}
	if m.snapshotConfig().CallbackURL == "" {
		writeJSON(w, http.StatusBadRequest, map[string]string{"message": "gateway is not configured"})
		return
	}
	status := m.snapshotStatus()
	if m.client.IsConnected() || status.Connected || status.SessionStatus == "connecting" || status.SessionStatus == "pairing" {
		writeJSON(w, http.StatusOK, status)
		return
	}

	if m.client.Store.ID == nil {
		qrChan, err := m.client.GetQRChannel(context.Background())
		if err != nil {
			writeJSON(w, http.StatusInternalServerError, map[string]string{"message": err.Error()})
			return
		}
		go m.consumeQR(qrChan)
	}

	m.updateStatus(func(status *SessionStatus) {
		status.SessionStatus = "connecting"
		status.LastError = ""
	})

	if err := m.client.Connect(); err != nil {
		m.updateStatus(func(status *SessionStatus) {
			status.SessionStatus = "error"
			status.LastError = err.Error()
		})
		writeJSON(w, http.StatusInternalServerError, map[string]string{"message": err.Error()})
		return
	}
	writeJSON(w, http.StatusOK, m.snapshotStatus())
}

func (m *Manager) handleDisconnect(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeJSON(w, http.StatusMethodNotAllowed, map[string]string{"message": "method not allowed"})
		return
	}
	m.client.Disconnect()
	m.updateStatus(func(status *SessionStatus) {
		status.Connected = false
		status.SessionStatus = "disconnected"
	})
	writeJSON(w, http.StatusOK, m.snapshotStatus())
}

func (m *Manager) handleStatus(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		writeJSON(w, http.StatusMethodNotAllowed, map[string]string{"message": "method not allowed"})
		return
	}
	writeJSON(w, http.StatusOK, m.snapshotStatus())
}

func (m *Manager) consumeQR(ch <-chan whatsmeow.QRChannelItem) {
	for item := range ch {
		switch item.Event {
		case "code":
			dataURL, err := qrCodeDataURL(item.Code)
			if err != nil {
				m.updateStatus(func(status *SessionStatus) {
					status.SessionStatus = "error"
					status.LastError = err.Error()
				})
				continue
			}
			m.updateStatus(func(status *SessionStatus) {
				status.SessionStatus = "pairing"
				status.QRCodeText = item.Code
				status.QRCodeDataURL = dataURL
				status.LastEvent = "code"
				status.LastError = ""
			})
		default:
			m.updateStatus(func(status *SessionStatus) {
				status.LastEvent = item.Event
				if item.Event == "success" {
					status.SessionStatus = "connected"
					status.Connected = true
					status.QRCodeDataURL = ""
					status.QRCodeText = ""
				}
				if strings.Contains(item.Event, "timeout") || strings.Contains(item.Event, "err") {
					status.SessionStatus = "error"
					status.LastError = item.Event
				}
			})
		}
	}
}

func (m *Manager) handleEvent(raw interface{}) {
	switch evt := raw.(type) {
	case *events.Connected:
		pairedPhone := ""
		if m.client.Store.ID != nil {
			pairedPhone = m.client.Store.ID.User
		}
		m.updateStatus(func(status *SessionStatus) {
			status.Connected = true
			status.SessionStatus = "connected"
			status.PairedPhone = pairedPhone
			status.QRCodeDataURL = ""
			status.QRCodeText = ""
			status.LastEvent = "connected"
			status.LastError = ""
		})
	case *events.LoggedOut:
		m.updateStatus(func(status *SessionStatus) {
			status.Connected = false
			status.SessionStatus = "logged_out"
			status.LastEvent = "logged_out"
		})
	case *events.Message:
		if evt.Info.IsFromMe {
			return
		}
		if !isSupportedInboundChat(evt.Info.Chat) {
			return
		}
		messageText := extractText(evt.Message)
		attachments := extractAttachments(m.client, m.dataDir, evt)
		if strings.TrimSpace(messageText) == "" && len(attachments) == 0 {
			return
		}
		go m.forwardInbound(evt, messageText, attachments)
	}
}

func isSupportedInboundChat(chat types.JID) bool {
	switch chat.Server {
	case types.DefaultUserServer, types.HiddenUserServer:
		return true
	default:
		return false
	}
}

func normalizeUserJID(ctx context.Context, client *whatsmeow.Client, jid types.JID) types.JID {
	if client == nil || jid.Server != types.HiddenUserServer {
		return jid
	}
	pn, err := client.Store.LIDs.GetPNForLID(ctx, jid.ToNonAD())
	if err != nil || pn.IsEmpty() {
		return jid
	}
	pn.Device = jid.Device
	return pn
}

func (m *Manager) forwardInbound(evt *events.Message, messageText string, attachments []MediaAttachment) {
	cfg := m.snapshotConfig()
	if cfg.CallbackURL == "" {
		m.updateStatus(func(status *SessionStatus) {
			status.LastError = "callback url not configured"
		})
		return
	}

	ctx := context.Background()
	chatJID := normalizeUserJID(ctx, m.client, evt.Info.Chat)
	senderJID := normalizeUserJID(ctx, m.client, evt.Info.Sender)
	sender := senderJID.String()
	if sender == "" {
		sender = chatJID.String()
	}
	payload := InboundPayload{
		TenantID:      cfg.TenantID,
		IntegrationID: cfg.IntegrationID,
		ChatID:        chatJID.String(),
		SenderID:      sender,
		SenderName:    evt.Info.PushName,
		MessageID:     evt.Info.ID,
		MessageText:   messageText,
		PushName:      evt.Info.PushName,
		SentAt:        evt.Info.Timestamp,
		Attachments:   attachments,
	}

	body, err := json.Marshal(payload)
	if err != nil {
		m.updateStatus(func(status *SessionStatus) { status.LastError = err.Error() })
		return
	}

	req, err := http.NewRequest(http.MethodPost, cfg.CallbackURL, bytes.NewReader(body))
	if err != nil {
		m.updateStatus(func(status *SessionStatus) { status.LastError = err.Error() })
		return
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("X-WhatsApp-Gateway-Secret", cfg.CallbackSecret)

	response, err := http.DefaultClient.Do(req)
	if err != nil {
		m.updateStatus(func(status *SessionStatus) { status.LastError = err.Error() })
		return
	}
	defer response.Body.Close()

	if response.StatusCode >= 400 {
		m.updateStatus(func(status *SessionStatus) { status.LastError = fmt.Sprintf("callback status %d", response.StatusCode) })
		return
	}

	var inboundResponse InboundResponse
	if err := json.NewDecoder(response.Body).Decode(&inboundResponse); err != nil {
		m.updateStatus(func(status *SessionStatus) { status.LastError = err.Error() })
		return
	}
	if inboundResponse.Duplicate || (strings.TrimSpace(inboundResponse.ReplyText) == "" && len(inboundResponse.ReplyFragments) == 0) {
		return
	}

	jid, err := types.ParseJID(payload.ChatID)
	if err != nil {
		m.updateStatus(func(status *SessionStatus) { status.LastError = err.Error() })
		return
	}
	if err = sendFragmentedReply(context.Background(), m.client, jid, inboundResponse.ReplyFragments, inboundResponse.ReplyText); err != nil {
		m.updateStatus(func(status *SessionStatus) { status.LastError = err.Error() })
		return
	}
}

func extractText(message *waProto.Message) string {
	if message == nil {
		return ""
	}
	if text := strings.TrimSpace(message.GetConversation()); text != "" {
		return text
	}
	if extended := message.GetExtendedTextMessage(); extended != nil {
		if text := strings.TrimSpace(extended.GetText()); text != "" {
			return text
		}
	}
	if image := message.GetImageMessage(); image != nil {
		if caption := strings.TrimSpace(image.GetCaption()); caption != "" {
			return caption
		}
	}
	if video := message.GetVideoMessage(); video != nil {
		if caption := strings.TrimSpace(video.GetCaption()); caption != "" {
			return caption
		}
	}
	if document := message.GetDocumentMessage(); document != nil {
		if caption := strings.TrimSpace(document.GetCaption()); caption != "" {
			return caption
		}
	}
	return ""
}

func extractAttachments(client *whatsmeow.Client, dataDir string, evt *events.Message) []MediaAttachment {
	if evt == nil || evt.Message == nil {
		return nil
	}

	if image := evt.Message.GetImageMessage(); image != nil {
		if attachment, err := storeDownloadedMedia(client, dataDir, evt, "image", image.GetMimetype(), image.GetCaption(), image); err == nil {
			return []MediaAttachment{attachment}
		}
	}
	if audio := evt.Message.GetAudioMessage(); audio != nil {
		if attachment, err := storeDownloadedMedia(client, dataDir, evt, "audio", audio.GetMimetype(), "", audio); err == nil {
			return []MediaAttachment{attachment}
		}
	}
	if video := evt.Message.GetVideoMessage(); video != nil {
		if attachment, err := storeDownloadedMedia(client, dataDir, evt, "video", video.GetMimetype(), video.GetCaption(), video); err == nil {
			return []MediaAttachment{attachment}
		}
	}
	if document := evt.Message.GetDocumentMessage(); document != nil {
		if attachment, err := storeDownloadedMedia(client, dataDir, evt, "document", document.GetMimetype(), document.GetCaption(), document); err == nil {
			return []MediaAttachment{attachment}
		}
	}
	return nil
}

func storeDownloadedMedia(client *whatsmeow.Client, dataDir string, evt *events.Message, kind string, mimeType string, caption string, downloadable interface{}) (MediaAttachment, error) {
	mediaMsg, ok := downloadable.(interface {
		GetDirectPath() string
		GetMediaKey() []byte
		GetFileSHA256() []byte
		GetFileEncSHA256() []byte
	})
	if !ok {
		return MediaAttachment{}, errors.New("unsupported media payload")
	}
	_ = mediaMsg
	attachmentType := kind
	if attachmentType == "" {
		attachmentType = "file"
	}

	payload, err := client.Download(context.Background(), mediaMsg)
	if err != nil {
		return MediaAttachment{}, err
	}

	ext := guessMediaExtension(kind, mimeType)
	filename := buildMediaFilename(evt.Info.ID, attachmentType, ext)
	mediaDir := filepath.Join(dataDir, "media")
	if err := os.MkdirAll(mediaDir, 0o755); err != nil {
		return MediaAttachment{}, err
	}
	fullPath := filepath.Join(mediaDir, filename)
	if err := os.WriteFile(fullPath, payload, 0o600); err != nil {
		return MediaAttachment{}, err
	}

	baseURL := "http://whatsapp-gateway:8090"
	return MediaAttachment{
		Kind:     attachmentType,
		FileRef:  baseURL + "/api/v1/media/" + url.PathEscape(filename),
		MimeType: mimeType,
		Caption:  strings.TrimSpace(caption),
		Filename: filename,
	}, nil
}

func guessMediaExtension(kind string, mimeType string) string {
	mimeType = strings.ToLower(strings.TrimSpace(mimeType))
	if mimeType != "" {
		if exts, err := mime.ExtensionsByType(mimeType); err == nil && len(exts) > 0 {
			return exts[0]
		}
		switch {
		case strings.Contains(mimeType, "ogg"):
			return ".ogg"
		case strings.Contains(mimeType, "opus"):
			return ".opus"
		case strings.Contains(mimeType, "mpeg"):
			return ".mp3"
		case strings.Contains(mimeType, "wav"):
			return ".wav"
		case strings.Contains(mimeType, "jpeg"):
			return ".jpg"
		case strings.Contains(mimeType, "png"):
			return ".png"
		case strings.Contains(mimeType, "webp"):
			return ".webp"
		case strings.Contains(mimeType, "mp4"):
			if kind == "audio" {
				return ".m4a"
			}
			return ".mp4"
		}
	}
	switch kind {
	case "image":
		return ".jpg"
	case "audio":
		return ".ogg"
	case "video":
		return ".mp4"
	case "document":
		return ".pdf"
	default:
		return ""
	}
}

func buildMediaFilename(messageID string, kind string, ext string) string {
	base := sanitizeFilename(messageID)
	if base == "" {
		base = "media"
	}
	k := sanitizeFilename(kind)
	if k != "" {
		base = base + "-" + k
	}
	ts := time.Now().UTC().Format("20060102T150405.000000000Z")
	return fmt.Sprintf("%s-%s%s", base, ts, ext)
}

func sanitizeFilename(value string) string {
	value = strings.ToLower(strings.TrimSpace(value))
	var builder strings.Builder
	for _, r := range value {
		switch {
		case unicode.IsLetter(r), unicode.IsDigit(r), r == '-', r == '_':
			builder.WriteRune(r)
		case r == '.' || r == '/':
			builder.WriteRune('-')
		}
	}
	return strings.Trim(builder.String(), "-_")
}

func (m *Manager) handleMedia(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		writeJSON(w, http.StatusMethodNotAllowed, map[string]string{"message": "method not allowed"})
		return
	}
	name := strings.TrimPrefix(r.URL.Path, "/api/v1/media/")
	name = filepath.Base(name)
	if name == "." || name == "/" || name == "" {
		writeJSON(w, http.StatusBadRequest, map[string]string{"message": "invalid media reference"})
		return
	}
	fullPath := filepath.Join(m.dataDir, "media", name)
	if _, err := os.Stat(fullPath); err != nil {
		writeJSON(w, http.StatusNotFound, map[string]string{"message": "media not found"})
		return
	}
	if contentType := mime.TypeByExtension(filepath.Ext(name)); contentType != "" {
		w.Header().Set("Content-Type", contentType)
	}
	http.ServeFile(w, r, fullPath)
}

func chunkReplyText(text string, maxChars int) []string {
	text = strings.TrimSpace(text)
	if text == "" {
		return nil
	}
	parts := strings.Fields(text)
	if len(parts) == 0 {
		return []string{text}
	}

	var chunks []string
	current := ""
	for _, part := range parts {
		candidate := part
		if current != "" {
			candidate = current + " " + part
		}
		if len(candidate) <= maxChars {
			current = candidate
			continue
		}
		if current != "" {
			chunks = append(chunks, strings.TrimSpace(current))
		}
		current = part
	}
	if current != "" {
		chunks = append(chunks, strings.TrimSpace(current))
	}
	return chunks
}

func sendFragmentedReply(ctx context.Context, client *whatsmeow.Client, jid types.JID, fragments []string, fallback string) error {
	toSend := fragments
	if len(toSend) == 0 {
		toSend = chunkReplyText(fallback, 180)
	}
	if len(toSend) == 0 {
		return nil
	}

	for idx, fragment := range toSend {
		fragment = strings.TrimSpace(fragment)
		if fragment == "" {
			continue
		}
		_, err := client.SendMessage(ctx, jid, &waProto.Message{Conversation: proto.String(fragment)})
		if err != nil {
			return err
		}
		if idx < len(toSend)-1 {
			time.Sleep(650 * time.Millisecond)
		}
	}
	return nil
}

func qrCodeDataURL(raw string) (string, error) {
	png, err := qrcode.Encode(raw, qrcode.Medium, 256)
	if err != nil {
		return "", err
	}
	return "data:image/png;base64," + base64.StdEncoding.EncodeToString(png), nil
}

func writeJSON(w http.ResponseWriter, statusCode int, payload interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(statusCode)
	_ = json.NewEncoder(w).Encode(payload)
}

func getenv(key string, fallback string) string {
	value := strings.TrimSpace(os.Getenv(key))
	if value == "" {
		return fallback
	}
	return value
}
