//go:build windows

package main

import (
	"log"

	"golang.org/x/sys/windows/svc"
)

// winServiceName must match the service name used by install.ps1's
// New-Service / sc.exe registration ("PyMonNOC").
const winServiceName = "PyMonNOC"

// runService is the entry point used when pymon.exe is invoked as
// `pymon service ...`. When launched by the Windows Service Control Manager
// (non-interactive session) it speaks the SCM protocol via golang.org/x/sys/windows/svc
// so the process can be managed with Start-Service/Stop-Service/Restart-Service
// like a systemd unit on Linux. When run from an interactive console (e.g. for
// manual debugging) it behaves like `pymon server`.
func runService(args []string) {
	isSvc, err := svc.IsWindowsService()
	if err != nil {
		log.Fatalf("service: cannot determine session type: %v", err)
	}
	if !isSvc {
		runServer(args)
		return
	}
	if err := svc.Run(winServiceName, &pymonService{args: args}); err != nil {
		log.Fatalf("service: %v", err)
	}
}

type pymonService struct {
	args []string
}

// Execute implements svc.Handler. It starts the HTTP server/monitor via the
// shared startApp helper and translates SCM stop/shutdown control requests
// into a graceful shutdown, mirroring the SIGTERM handling used on Linux.
func (s *pymonService) Execute(_ []string, r <-chan svc.ChangeRequest, changes chan<- svc.Status) (svcSpecificEC bool, exitCode uint32) {
	const accepted = svc.AcceptStop | svc.AcceptShutdown

	changes <- svc.Status{State: svc.StartPending}

	_, _, shutdown, done := startApp(s.args)

	changes <- svc.Status{State: svc.Running, Accepts: accepted}

	for {
		select {
		case err := <-done:
			if err != nil {
				log.Printf("service: server exited with error: %v", err)
				changes <- svc.Status{State: svc.Stopped}
				return false, 1
			}
			changes <- svc.Status{State: svc.Stopped}
			return false, 0
		case req := <-r:
			switch req.Cmd {
			case svc.Interrogate:
				changes <- req.CurrentStatus
			case svc.Stop, svc.Shutdown:
				changes <- svc.Status{State: svc.StopPending}
				shutdown()
				// Wait for the server goroutine to actually finish so we
				// don't report Stopped while it is still shutting down.
				<-done
				changes <- svc.Status{State: svc.Stopped}
				return false, 0
			}
		}
	}
}
