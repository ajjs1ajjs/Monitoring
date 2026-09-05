//go:build !windows

package main

// runService is a no-op alias for runServer on non-Windows platforms. The
// Windows Service Control Manager entry point (service_windows.go) is only
// meaningful on windows; elsewhere `pymon service` behaves exactly like
// `pymon server` so the same CLI works cross-platform without a build tag
// at the call site in main.go.
func runService(args []string) {
	runServer(args)
}
