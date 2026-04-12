package tools

import (
	"context"

	"github.com/google/go-github/v84/github"
	"github.com/modelcontextprotocol/go-sdk/mcp"
)

type GithubToolInput struct {
	UserName string `json:"user_name" jsonschema:"The GitHub username to interact with."`
	PerPage  *int   `json:"per_page,omitempty" jsonschema:"The number of items to return per page."`
	MaxPages *int   `json:"max_pages,omitempty" jsonschema:"The maximum number of pages to return."`
}

func (i *GithubToolInput) GetPerPage() int {
	if i.PerPage == nil || *i.PerPage < 1 {
		return 1
	}
	return *i.PerPage
}

func (i *GithubToolInput) GetMaxPages() int {
	if i.MaxPages == nil || *i.MaxPages < 1 {
		return 1
	}
	return *i.MaxPages
}

type GithubTool struct {
	client *github.Client
}

func NewGithubTool(server *mcp.Server) {
	ghTool := &GithubTool{
		client: github.NewClient(nil),
	}
	mcp.AddTool(
		server,
		&mcp.Tool{
			Name:        "github_list_user_repos",
			Description: "List repositories for a given GitHub user.",
		},
		ghTool.ListUserRepos,
	)
	mcp.AddTool(
		server,
		&mcp.Tool{
			Name:        "github_list_user_pull_requests",
			Description: "List pull requests for a given GitHub repository.",
		},
		ghTool.ListUserPullRequests,
	)
}

type ListUserReposInput struct {
	GithubToolInput
	Type string `json:"type" jsonschema:"The type of repositories to list." jsonschema_extras:"example=owner"`
	Sort string `json:"sort" jsonschema:"The sorting method for the repositories." jsonschema_extras:"example=created"`
}

type ListUserReposOutput struct {
	Repositories []string `json:"repositories" jsonschema:"The list of repository names."`
}

func (gh *GithubTool) ListUserRepos(ctx context.Context, req *mcp.CallToolRequest, input ListUserReposInput) (*mcp.CallToolResult, ListUserReposOutput, error) {
	maxPages := input.GetMaxPages()

	options := &github.RepositoryListByUserOptions{}
	var repoNames []string

	for page := 1; page <= maxPages; page++ {
		repos, response, err := gh.client.Repositories.ListByUser(ctx, input.UserName, options)
		if err != nil {
			return nil, ListUserReposOutput{}, err
		}

		for _, repo := range repos {
			repoNames = append(repoNames, repo.GetName())
		}

		if page == maxPages || response.NextPage == 0 {
			break
		}

		options.ListOptions.Page = response.NextPage
	}

	return nil, ListUserReposOutput{Repositories: repoNames}, nil
}

type ListUserPullRequestsInput struct {
	GithubToolInput
	RepoName string `json:"repo_name" jsonschema:"The name of the repository to list pull requests from." jsonschema_extras:"example=Hello-World"`
	State    string `json:"state" jsonschema:"The state of the pull requests to list (open, closed, all)." jsonschema_extras:"example=open"`
}

type ListUserPullRequestsOutput struct {
	PullRequests []string `json:"pull_requests" jsonschema:"The list of pull request urls."`
}

func (gh *GithubTool) ListUserPullRequests(ctx context.Context, req *mcp.CallToolRequest, input ListUserPullRequestsInput) (*mcp.CallToolResult, ListUserPullRequestsOutput, error) {
	maxPages := input.GetMaxPages()

	options := &github.PullRequestListOptions{
		State: input.State,
	}
	var prURLs []string

	for page := 1; page <= maxPages; page++ {
		prs, response, err := gh.client.PullRequests.List(ctx, input.UserName, input.RepoName, options)
		if err != nil {
			return nil, ListUserPullRequestsOutput{}, err
		}

		for _, pr := range prs {
			prURLs = append(prURLs, pr.GetHTMLURL())
		}

		if page == maxPages || response.NextPage == 0 {
			break
		}

		options.ListOptions.Page = response.NextPage
	}

	return nil, ListUserPullRequestsOutput{PullRequests: prURLs}, nil
}
