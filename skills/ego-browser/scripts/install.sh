#!/usr/bin/env bash
#v1.5 2026.06.04 17:16

set -euo pipefail

# Default package URL and installation paths.
DMG_URL_ARM64="https://cdn.ego.app/channel/egobrowser_npx_referral/setup/macos/arm64/egolite.dmg"
DMG_URL_X64="https://cdn.ego.app/channel/egobrowser_npx_referral/setup/macos/x64/egolite.dmg"
APP_NAME="ego lite"
APP_BUNDLE_NAME="$APP_NAME.app"
APP_PATH="/Applications/$APP_BUNDLE_NAME"
USER_APP_PATH="$HOME/Applications/$APP_BUNDLE_NAME"
EGO_BROWSER_HELPER_NAME="ego-browser"
EGO_BROWSER_BUNDLE_ID="com.citrolabs.ego.lite"
EGO_BROWSER_TEAM_ID="JGQLC6YQYJ"

# Temporary directories created when mounting the DMG; cleaned up on exit.
TEMP_DIR=""
MOUNT_DIR=""
DMG_ATTACHED=""

log() {
	printf '%s\n' "$*" >&2
}

die() {
	log "error: $*"
	exit 1
}

require_command() {
	command -v "$1" >/dev/null 2>&1 || die "missing required command: $1"
}

select_dmg_url() {
	if [ "$(uname -m)" = "arm64" ]; then
		printf '%s\n' "$DMG_URL_ARM64"
	else
		printf '%s\n' "$DMG_URL_X64"
	fi
}

run_with_privilege_for() {
	local writable_path="$1"
	shift
	if [ -w "$writable_path" ]; then
		"$@"
		return
	fi
	require_command sudo
	log "Administrator privileges are required for $writable_path."
	sudo "$@"
}

cleanup() {
	# Detach the DMG and remove the temp directory on success, failure, or Ctrl+C.
	if [ "$DMG_ATTACHED" = "1" ]; then
		if ! hdiutil detach "$MOUNT_DIR" -quiet >/dev/null 2>&1; then
			log "warning: failed to detach $MOUNT_DIR"
		else
			DMG_ATTACHED=""
		fi
	fi

	if [ -n "$TEMP_DIR" ] && [ -d "$TEMP_DIR" ]; then
		if [ "$DMG_ATTACHED" = "1" ]; then
			log "warning: skipping temp cleanup while DMG remains mounted"
		else
			rm -rf "$TEMP_DIR" >/dev/null 2>&1 ||
				log "warning: failed to remove temporary directory: $TEMP_DIR"
		fi
	fi
}

strip_quarantine_attributes() {
	local app_path="$1"
	if ! run_with_privilege_for "$app_path" xattr -dr com.apple.quarantine "$app_path" \
		>/dev/null 2>&1; then
		log "warning: failed to strip quarantine attribute on $app_path"
	fi
}

verify_ego_lite_app() {
	local app_path="$1"
	local bundle_id
	local signature
	local team_id
	require_command codesign
	require_command spctl

	codesign --verify --deep --strict "$app_path" ||
		die "invalid code signature on $app_path"
	signature=$(codesign -dv --verbose=4 "$app_path" 2>&1) ||
		die "cannot read code signature from $app_path"
	bundle_id=$(printf '%s\n' "$signature" | sed -n 's/^Identifier=//p')
	team_id=$(printf '%s\n' "$signature" | sed -n 's/^TeamIdentifier=//p')
	[ "$bundle_id" = "$EGO_BROWSER_BUNDLE_ID" ] ||
		die "unexpected bundle identifier on $app_path"
	[ "$team_id" = "$EGO_BROWSER_TEAM_ID" ] ||
		die "unexpected team identifier on $app_path"
	spctl --assess --type execute "$app_path" ||
		die "$app_path is not accepted by Gatekeeper"
}

verify_ego_lite_pkg() {
	local pkg_path="$1"
	local signature
	require_command pkgutil
	require_command spctl

	signature=$(pkgutil --check-signature "$pkg_path" 2>&1) ||
		die "invalid package signature on $pkg_path"
	case "$signature" in
	*"Developer ID Installer: CITRO LABS PTE. LIMITED ($EGO_BROWSER_TEAM_ID)"*) ;;
	*) die "unexpected publisher signature on $pkg_path" ;;
	esac
	spctl --assess --type install "$pkg_path" ||
		die "$pkg_path is not accepted by Gatekeeper"
}

trap cleanup EXIT HUP INT TERM

find_ego_browser_in_app() {
	local app_path="$1"
	local candidate

	[ -d "$app_path/Contents" ] || return 1

	# A Chromium app bundle may contain multiple versions; prefer the one under Current.
	for candidate in "$app_path"/Contents/Frameworks/*.framework/Versions/Current/Helpers/"$EGO_BROWSER_HELPER_NAME"; do
		if [ -x "$candidate" ]; then
			printf '%s\n' "$candidate"
			return 0
		fi
	done

	# ego-browser may live in various locations inside the bundle; search under Contents.
	while IFS= read -r candidate; do
		if [ -x "$candidate" ]; then
			printf '%s\n' "$candidate"
			return 0
		fi
	done < <(find "$app_path/Contents" -type f -name "$EGO_BROWSER_HELPER_NAME" 2>/dev/null)

	return 1
}

is_ego_lite_app() {
	local app_path="$1"

	# The directory exists and contains a working ego-browser - ego lite is considered installed.
	[ -d "$app_path" ] || return 1
	find_ego_browser_in_app "$app_path" >/dev/null
}

find_ego_lite_app() {
	local app_path
	local apps_dir

	for app_path in "$APP_PATH" "$USER_APP_PATH"; do
		if is_ego_lite_app "$app_path"; then
			printf '%s\n' "$app_path"
			return 0
		fi
	done

	for apps_dir in "$(dirname "$APP_PATH")" "$(dirname "$USER_APP_PATH")"; do
		[ -d "$apps_dir" ] || continue

		while IFS= read -r app_path; do
			if is_ego_lite_app "$app_path"; then
				printf '%s\n' "$app_path"
				return 0
			fi
		done < <(find "$apps_dir" -maxdepth 1 -type d -iname "$APP_BUNDLE_NAME" 2>/dev/null)
	done

	return 1
}

install_ego_lite() {
	local temp_base_dir
	local dmg_path
	local dmg_url
	local app_in_dmg
	local staged_app
	local pkg_in_dmg

	require_command curl
	require_command hdiutil

	# Download and mount the DMG in an isolated temp directory to avoid polluting the CWD.
	temp_base_dir=${TMPDIR:-/tmp}
	temp_base_dir=${temp_base_dir%/}
	TEMP_DIR=$(mktemp -d "$temp_base_dir/ego-lite-install.XXXXXX")
	MOUNT_DIR="$TEMP_DIR/mount"
	dmg_path="$TEMP_DIR/egolite.dmg"
	dmg_url=$(select_dmg_url)
	mkdir -p "$MOUNT_DIR"

	log "$APP_NAME is not installed. Downloading $dmg_url ..."
	curl -fL --retry 3 --output "$dmg_path" "$dmg_url" ||
		die "failed to download $APP_NAME from $dmg_url"

	log "Mounting installer ..."
	hdiutil attach "$dmg_path" -nobrowse -readonly -mountpoint "$MOUNT_DIR" \
		>/dev/null
	DMG_ATTACHED="1"

	# Handle DMGs that contain the app bundle directly.
	app_in_dmg=$(
		find "$MOUNT_DIR" -maxdepth 2 \
			-type d -iname "$APP_BUNDLE_NAME" -print -quit
	)

	if [ -n "$app_in_dmg" ]; then
		staged_app="$TEMP_DIR/$APP_BUNDLE_NAME"

		require_command ditto
		log "Installing $APP_NAME to $APP_PATH ..."
		ditto "$app_in_dmg" "$staged_app" ||
			die "failed to stage $APP_NAME from installer"
		find_ego_browser_in_app "$staged_app" >/dev/null ||
			die "installed $APP_NAME does not contain $EGO_BROWSER_HELPER_NAME"
		verify_ego_lite_app "$staged_app"

		if [ -d "$APP_PATH" ]; then
			[ "$APP_PATH" = "/Applications/$APP_BUNDLE_NAME" ] ||
				die "refusing to replace unexpected app path: $APP_PATH"
			run_with_privilege_for "$(dirname "$APP_PATH")" rm -rf "$APP_PATH" ||
				die "failed to replace existing $APP_PATH"
		fi
		run_with_privilege_for "$(dirname "$APP_PATH")" mv "$staged_app" "$APP_PATH" ||
			die "failed to move $APP_NAME to $APP_PATH"
		return 0
	fi

	# Fall back to pkg installer if the DMG contains a .pkg instead of an app bundle.
	pkg_in_dmg=$(
		find "$MOUNT_DIR" -maxdepth 2 -type f -name "*.pkg" -print -quit
	)

	if [ -n "$pkg_in_dmg" ]; then
		verify_ego_lite_pkg "$pkg_in_dmg"
		log "Installing $APP_NAME package ..."
		run_with_privilege_for / installer -pkg "$pkg_in_dmg" -target / ||
			die "failed to install $APP_NAME package"
		return 0
	fi

	die "cannot find $APP_NAME app or pkg in mounted DMG"
}

main() {
	local installed_app_path

	[ "$(uname -s)" = "Darwin" ] || die "this script only supports macOS"

	# Install first if not present; otherwise use the ego-browser bundled inside the app.
	installed_app_path=$(find_ego_lite_app || true)
	if [ -z "$installed_app_path" ]; then
		install_ego_lite
		installed_app_path=$(find_ego_lite_app || true)
		[ -n "$installed_app_path" ] ||
			die "$APP_NAME install completed, but app was not found"
	fi

	verify_ego_lite_app "$installed_app_path"
	strip_quarantine_attributes "$installed_app_path"
	cleanup

	log "Launching $APP_NAME ..."
	exec open "$installed_app_path"
}

main "$@"
