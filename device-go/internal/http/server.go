package http

import (
    "context"
    "fmt"
    "log"
    "net/http"

    "github.com/gorilla/mux"
)

type Server struct {
    srv    *http.Server
    router *mux.Router
    port   int
}

func NewServer(handlers *Handlers, port int) *Server {
    r := mux.NewRouter()
    r.HandleFunc("/api/commands", handlers.SendCommand).Methods("POST", "OPTIONS") // разрешаем OPTIONS
    r.HandleFunc("/api/commands/list", handlers.ListCommands).Methods("GET", "OPTIONS")
    r.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
        w.WriteHeader(http.StatusOK)
        w.Write([]byte("OK"))
    }).Methods("GET", "OPTIONS")

    // Оборачиваем роутер в CORS middleware
    handlerWithCORS := CORS(r)

    srv := &http.Server{
        Addr:    fmt.Sprintf(":%d", port),
        Handler: handlerWithCORS,
    }

    return &Server{
        srv:    srv,
        router: r,
        port:   port,
    }
}

func (s *Server) Start() error {
    log.Printf("HTTP server listening on %s", s.srv.Addr)
    return s.srv.ListenAndServe()
}

func (s *Server) Shutdown(ctx context.Context) error {
    return s.srv.Shutdown(ctx)
}