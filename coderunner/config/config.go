package config

import (
	"os"
	"strings"
)

type Config struct {
	RemoteHosts []string
	AppUserName string
}

func (c *Config) ReloadConfig() {
	c = newConfig()
}

func newConfig() *Config {
	remoteHosts := os.Getenv("REMOTE_HOSTS")
	return &Config{
		RemoteHosts: strings.Split(remoteHosts, ";"),
		AppUserName: os.Getenv("APP_USER_NAME"),
	}
}

var Conf = newConfig()
