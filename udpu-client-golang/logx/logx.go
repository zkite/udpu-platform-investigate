package logx

import (
	"log"
	"os"
	"sync/atomic"
)

// Package-level loggers.
// Info is always printed. Debug prints only when enabled.
var (
	InfoLogger  = log.New(os.Stdout, "INFO  ", log.LstdFlags|log.Lmicroseconds)
	DebugLogger = log.New(os.Stdout, "DEBUG ", log.LstdFlags|log.Lmicroseconds)
	FatalLogger = log.New(os.Stderr, "FATAL ", log.LstdFlags|log.Lmicroseconds)
)

// debug holds global debug state.
var debug atomic.Bool

// SetDebug enables or disables debug logging globally.
func SetDebug(enabled bool) { debug.Store(enabled) }

// IsDebug reports current global debug state.
func IsDebug() bool { return debug.Load() }

// Infof logs informational messages.
func Infof(format string, v ...any) { InfoLogger.Printf(format, v...) }

// Debugf logs debug messages when debug is enabled.
func Debugf(format string, v ...any) {
	if IsDebug() {
		DebugLogger.Printf(format, v...)
	}
}

// Fatalf logs and exits with non-zero status.
// Semantics match log.Fatalf (prints then os.Exit(1)).
func Fatalf(format string, v ...any) {
	FatalLogger.Printf(format, v...)
	os.Exit(1)
}
