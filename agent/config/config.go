package config

type Config struct {
	DockerApiVersion string
	WorkerPort       string
	MinActive        int
}

func NewConfig() *Config {
	return &Config{
		DockerApiVersion: "1.40",
		WorkerPort:       ":30031",
		MinActive:        2,
	}
}
