#!/usr/bin/env bash

set -euo pipefail

REPO="mosteligible/mcp-codemode"
GO_INSTALL_TARGET="github.com/mosteligible/mcp-codemode/agent@latest"
SERVICE_NAME="mcp-codemode-agent"
SERVICE_USER="mcp-codemode-agent"
SERVICE_GROUP="mcp-codemode-agent"
INSTALL_DIR="/usr/local/bin"
BINARY_NAME="mcp-codemode-agent"
INSTALL_PATH="${INSTALL_DIR}/${BINARY_NAME}"
CONFIG_DIR="/etc/${SERVICE_NAME}"
ENV_FILE="${CONFIG_DIR}/agent.env"
STATE_DIR="/var/lib/${SERVICE_NAME}"
UNIT_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

DOCKER_API_VERSION_DEFAULT="1.40"
DOCKER_IMAGE_NAME_DEFAULT="python:3.14-slim"
WORKER_PORT_DEFAULT=":30031"
MIN_ACTIVE_DEFAULT="2"
ACTIVE_CONTAINER_CHECK_INTERVAL_DEFAULT="30"

DOWNLOAD_TOOL=""
TMP_DIR=""
ARCH=""
RELEASE_TAG=""
USE_SUDO=""
DOCKER_SOCKET_GROUP=""

cleanup() {
	if [[ -n "${TMP_DIR}" && -d "${TMP_DIR}" ]]; then
		rm -rf "${TMP_DIR}"
	fi
}

trap cleanup EXIT

warn() {
	printf '[setup] warning: %s\n' "$*" >&2
}

fail() {
	printf '[setup] error: %s\n' "$*" >&2
	exit 1
}

run_cmd() {
	if [[ -n "${USE_SUDO}" ]]; then
		sudo "$@"
		return
	fi

	"$@"
}

write_root_file() {
	local destination="$1"
	local mode="$2"
	local owner="$3"
	local group="$4"
	local source_file="$5"

	run_cmd install -d -m 0755 "$(dirname "${destination}")"
	run_cmd install -m "${mode}" -o "${owner}" -g "${group}" "${source_file}" "${destination}"
}

ensure_root() {
	if [[ "${EUID}" -eq 0 ]]; then
		return
	fi

	if command -v sudo >/dev/null 2>&1; then
		USE_SUDO="sudo"
		return
	fi

	fail "run this script as root or install sudo"
}

require_command() {
	local command_name="$1"
	if ! command -v "${command_name}" >/dev/null 2>&1; then
		fail "required command not found: ${command_name}"
	fi
}

detect_download_tool() {
	if command -v curl >/dev/null 2>&1; then
		DOWNLOAD_TOOL="curl"
		return
	fi

	if command -v wget >/dev/null 2>&1; then
		DOWNLOAD_TOOL="wget"
		return
	fi

	fail "either curl or wget must be installed"
}

http_get() {
	local url="$1"

	if [[ "${DOWNLOAD_TOOL}" == "curl" ]]; then
		curl --fail --silent --show-error --location \
			-H 'Accept: application/vnd.github+json' \
			-H 'X-GitHub-Api-Version: 2022-11-28' \
			"${url}"
		return
	fi

	wget -qO- \
		--header='Accept: application/vnd.github+json' \
		--header='X-GitHub-Api-Version: 2022-11-28' \
		"${url}"
}

download_file() {
	local url="$1"
	local output="$2"

	if [[ "${DOWNLOAD_TOOL}" == "curl" ]]; then
		curl --fail --silent --show-error --location -o "${output}" "${url}"
		return
	fi

	wget -qO "${output}" "${url}"
}

detect_architecture() {
	case "$(uname -m)" in
		x86_64|amd64)
			ARCH="amd64"
			;;
		aarch64|arm64)
			ARCH="arm64"
			;;
		*)
			fail "unsupported architecture: $(uname -m)"
			;;
	esac
}

validate_platform() {
	if [[ "$(uname -s)" != "Linux" ]]; then
		fail "this installer supports Linux hosts only"
	fi

	require_command tar
	require_command systemctl
	require_command docker
}

validate_docker() {
	if ! docker info >/dev/null 2>&1; then
		fail "docker daemon is not available; start docker before running this installer"
	fi

	if docker info --format '{{.DefaultRuntime}}' >/dev/null 2>&1; then
		local default_runtime
		default_runtime="$(docker info --format '{{.DefaultRuntime}}')"
		if [[ "${default_runtime}" != "runsc" ]]; then
			warn "docker default runtime is '${default_runtime}', not 'runsc'; agent containers will not use gVisor unless docker is configured accordingly"
		fi
	fi
}

latest_release_json() {
	http_get "https://api.github.com/repos/${REPO}/releases/latest"
}

extract_release_tag() {
	sed -n 's/.*"tag_name"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -n 1
}

extract_asset_url() {
	local asset_name="$1"
	sed -n "s/.*\"browser_download_url\"[[:space:]]*:[[:space:]]*\"\([^\"]*${asset_name}[^\"]*\)\".*/\1/p" | head -n 1
}

validate_archive_paths() {
	local archive_path="$1"
	local entry

	while IFS= read -r entry; do
		if [[ -z "${entry}" ]]; then
			warn "release archive contains an empty path entry"
			return 1
		fi

		if [[ "${entry}" == /* ]]; then
			warn "release archive contains an absolute path: ${entry}"
			return 1
		fi

		if [[ "${entry}" == ".." || "${entry}" == ../* || "${entry}" == */../* || "${entry}" == */.. ]]; then
			warn "release archive contains a path traversal entry: ${entry}"
			return 1
		fi
	done < <(tar -tzf "${archive_path}")

	return 0
}

install_binary_from_release() {
	local release_json
	local asset_name
	local asset_url
	local archive_path
	local extracted_binary
	local unpack_dir

	printf '[setup] %s\n' "looking up latest GitHub release for ${REPO}"
	if ! release_json="$(latest_release_json 2>/dev/null)"; then
		warn "could not query the latest GitHub release; falling back to go install"
		return 1
	fi

	RELEASE_TAG="$(printf '%s' "${release_json}" | extract_release_tag)"
	if [[ -z "${RELEASE_TAG}" ]]; then
		warn "latest GitHub release response did not contain a tag; falling back to go install"
		return 1
	fi

	asset_name="agent_linux_${ARCH}.tar.gz"
	asset_url="$(printf '%s' "${release_json}" | extract_asset_url "${asset_name}")"
	if [[ -z "${asset_url}" ]]; then
		warn "release ${RELEASE_TAG} does not contain ${asset_name}; falling back to go install"
		return 1
	fi

	archive_path="${TMP_DIR}/${asset_name}"
	unpack_dir="${TMP_DIR}/release"
	if ! mkdir -p "${unpack_dir}"; then
		warn "failed to create temporary directory for release extraction; falling back to go install"
		return 1
	fi

	printf '[setup] %s\n' "downloading ${asset_name} from release ${RELEASE_TAG}"
	if ! download_file "${asset_url}" "${archive_path}"; then
		warn "failed to download ${asset_name} from release ${RELEASE_TAG}; falling back to go install"
		return 1
	fi

	if ! validate_archive_paths "${archive_path}"; then
		warn "release archive ${asset_name} failed path validation; falling back to go install"
		return 1
	fi

	if ! tar -xzf "${archive_path}" -C "${unpack_dir}"; then
		warn "failed to extract ${asset_name} from release ${RELEASE_TAG}; falling back to go install"
		return 1
	fi

	extracted_binary="$(find "${unpack_dir}" -mindepth 1 -maxdepth 2 -type f -name agent | head -n 1)"
	if [[ -z "${extracted_binary}" ]]; then
		warn "release archive ${asset_name} does not contain an agent binary; falling back to go install"
		return 1
	fi

	if ! run_cmd install -d -m 0755 "${INSTALL_DIR}"; then
		fail "failed to create install directory ${INSTALL_DIR}"
	fi

	if ! run_cmd install -m 0755 "${extracted_binary}" "${INSTALL_PATH}"; then
		fail "failed to install ${BINARY_NAME} from release ${RELEASE_TAG}"
	fi

	printf '[setup] %s\n' "installed ${BINARY_NAME} from GitHub release ${RELEASE_TAG}"
	return 0
}

install_binary_from_go() {
	local gobin
	local installed_binary

	require_command go

	gobin="${TMP_DIR}/gobin"
	mkdir -p "${gobin}"

	printf '[setup] %s\n' "installing agent via go install fallback"
	GOBIN="${gobin}" go install "${GO_INSTALL_TARGET}"

	installed_binary="${gobin}/agent"
	if [[ ! -f "${installed_binary}" ]]; then
		fail "go install completed without producing ${installed_binary}"
	fi

	run_cmd install -d -m 0755 "${INSTALL_DIR}"
	run_cmd install -m 0755 "${installed_binary}" "${INSTALL_PATH}"
	RELEASE_TAG="go-install"
	printf '[setup] %s\n' "installed ${BINARY_NAME} via go install fallback"
}

ensure_binary_installed() {
	if install_binary_from_release; then
		return
	fi

	install_binary_from_go
}

stop_service_if_running() {
	if run_cmd systemctl is-active --quiet "${SERVICE_NAME}"; then
		printf '[setup] %s\n' "stopping ${SERVICE_NAME} before replacing the binary"
		run_cmd systemctl stop "${SERVICE_NAME}"
	fi
}

ensure_service_account() {
	if ! getent group "${SERVICE_GROUP}" >/dev/null 2>&1; then
		printf '[setup] %s\n' "creating system group ${SERVICE_GROUP}"
		run_cmd groupadd --system "${SERVICE_GROUP}"
	fi

	if ! id -u "${SERVICE_USER}" >/dev/null 2>&1; then
		printf '[setup] %s\n' "creating system user ${SERVICE_USER}"
		run_cmd useradd \
			--system \
			--gid "${SERVICE_GROUP}" \
			--home-dir "${STATE_DIR}" \
			--shell /usr/sbin/nologin \
			"${SERVICE_USER}"
	fi

	DOCKER_SOCKET_GROUP="$(stat -c '%G' /var/run/docker.sock 2>/dev/null || true)"
	if [[ -n "${DOCKER_SOCKET_GROUP}" && "${DOCKER_SOCKET_GROUP}" != "root" && "${DOCKER_SOCKET_GROUP}" != "UNKNOWN" ]]; then
		if id -nG "${SERVICE_USER}" | tr ' ' '\n' | grep -Fx "${DOCKER_SOCKET_GROUP}" >/dev/null 2>&1; then
			return
		fi

		printf '[setup] %s\n' "adding ${SERVICE_USER} to ${DOCKER_SOCKET_GROUP} for docker socket access"
		run_cmd usermod -aG "${DOCKER_SOCKET_GROUP}" "${SERVICE_USER}"
		return
	fi

	warn "could not determine a non-root group for /var/run/docker.sock; verify that ${SERVICE_USER} can reach the docker daemon"
}

write_env_file() {
	local temp_file

	temp_file="${TMP_DIR}/agent.env"
	cat >"${temp_file}" <<EOF
DOCKER_API_VERSION=${DOCKER_API_VERSION:-$DOCKER_API_VERSION_DEFAULT}
DOCKER_IMAGE_NAME=${DOCKER_IMAGE_NAME:-$DOCKER_IMAGE_NAME_DEFAULT}
WORKER_PORT=${WORKER_PORT:-$WORKER_PORT_DEFAULT}
MIN_ACTIVE=${MIN_ACTIVE:-$MIN_ACTIVE_DEFAULT}
ACTIVE_CONTAINER_CHECK_INTERVAL=${ACTIVE_CONTAINER_CHECK_INTERVAL:-$ACTIVE_CONTAINER_CHECK_INTERVAL_DEFAULT}
EOF

	run_cmd install -d -m 0755 "${CONFIG_DIR}"
	write_root_file "${ENV_FILE}" 0600 root root "${temp_file}"
}

write_unit_file() {
	local supplementary_groups
	local temp_file

	supplementary_groups=""
	if [[ -n "${DOCKER_SOCKET_GROUP}" ]] && getent group "${DOCKER_SOCKET_GROUP}" >/dev/null 2>&1; then
		supplementary_groups="SupplementaryGroups=${DOCKER_SOCKET_GROUP}"
	fi

	temp_file="${TMP_DIR}/${SERVICE_NAME}.service"
	cat >"${temp_file}" <<EOF
[Unit]
Description=MCP Codemode Agent
After=network-online.target docker.service
Wants=network-online.target docker.service
Requires=docker.service

[Service]
Type=simple
User=${SERVICE_USER}
Group=${SERVICE_GROUP}
${supplementary_groups}
EnvironmentFile=${ENV_FILE}
ExecStart=${INSTALL_PATH}
Restart=on-failure
RestartSec=5s
StateDirectory=${SERVICE_NAME}
WorkingDirectory=${STATE_DIR}
NoNewPrivileges=true

[Install]
WantedBy=multi-user.target
EOF

	write_root_file "${UNIT_FILE}" 0644 root root "${temp_file}"
}

enable_service() {
	printf '[setup] %s\n' "reloading systemd and enabling ${SERVICE_NAME}"
	run_cmd systemctl daemon-reload
	run_cmd systemctl enable "${SERVICE_NAME}"
	run_cmd systemctl restart "${SERVICE_NAME}"
}

print_summary() {
	cat <<EOF

Installed ${BINARY_NAME} to ${INSTALL_PATH}
Service name: ${SERVICE_NAME}
Environment file: ${ENV_FILE}
Release source: ${RELEASE_TAG}

Useful commands:
	systemctl status ${SERVICE_NAME}
	journalctl -u ${SERVICE_NAME} -f
	systemctl restart ${SERVICE_NAME}

If you update ${ENV_FILE}, restart the service for changes to take effect.
EOF
}

main() {
	ensure_root
	validate_platform
	detect_download_tool
	detect_architecture
	validate_docker

	TMP_DIR="$(mktemp -d)"

	stop_service_if_running
	ensure_binary_installed
	ensure_service_account
	write_env_file
	write_unit_file
	enable_service
	print_summary
}

main "$@"
