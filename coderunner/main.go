package main

import "github.com/mosteligible/mcp-codemode/coderunner/app"

func main() {
	app := app.NewApp(":8080")
	app.Start()
}
