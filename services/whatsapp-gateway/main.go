package main

import (
	"bytes"
	"context"
	"encoding/base64"
	"encoding/json"
	"errors"
	"fmt"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"

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
	TenantID      string    `json:"tenant_id"`
	IntegrationID string    `json:"integration_id"`
	ChatID        string    `json:"chat_id"`
	SenderID      string    `json:"sender_id"`
	SenderName    string    `json:"sender_name,omitempty"`
	MessageID     string    `json:"message_id"`
	MessageText   string    `json:"message_text"`
	PushName      string    `json:"push_name,omitempty"`
	SentAt        time.Time `json:"sent_at,omitempty"`
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

	ctx := context.Background()
	container, err := sqlstore.New(
		ctx,
		"sqlite",
		fmt.Sprintf("file:%s?_pragma=foreign_keys(1)", filepath.ToSlash(filepath.Join(dataDir, "session.db"))),
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
		if evt.Info.Chat.Server != types.DefaultUserServer {
			return
		}
		messageText := extractText(evt.Message)
		if strings.TrimSpace(messageText) == "" {
			return
		}
		go m.forwardInbound(evt, messageText)
	}
}

func (m *Manager) forwardInbound(evt *events.Message, messageText string) {
	cfg := m.snapshotConfig()
	if cfg.CallbackURL == "" {
		m.updateStatus(func(status *SessionStatus) {
			status.LastError = "callback url not configured"
		})
		return
	}

	sender := evt.Info.Sender.String()
	if sender == "" {
		sender = evt.Info.Chat.String()
	}
	payload := InboundPayload{
		TenantID:      cfg.TenantID,
		IntegrationID: cfg.IntegrationID,
		ChatID:        evt.Info.Chat.String(),
		SenderID:      sender,
		SenderName:    evt.Info.PushName,
		MessageID:     evt.Info.ID,
		MessageText:   messageText,
		PushName:      evt.Info.PushName,
		SentAt:        evt.Info.Timestamp,
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
	if inboundResponse.Duplicate || strings.TrimSpace(inboundResponse.ReplyText) == "" {
		return
	}

	jid, err := types.ParseJID(payload.ChatID)
	if err != nil {
		m.updateStatus(func(status *SessionStatus) { status.LastError = err.Error() })
		return
	}
	_, err = m.client.SendMessage(context.Background(), jid, &waProto.Message{Conversation: proto.String(inboundResponse.ReplyText)})
	if err != nil {
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
	return ""
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
