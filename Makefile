.PHONY: install

SYSDIR = /etc/systemd/system
APPDIR = /opt/pushkin-server
UNITS = $(SYSDIR)/pushkin-server.service
UNITSSRC = $(APPDIR)/support/pushkin-server.service

install : $(UNITS)

$(UNITS): $(UNITSSRC)
	cp $(APPDIR)/support/pushkin-server.service $(SYSDIR)/pushkin-server.service
