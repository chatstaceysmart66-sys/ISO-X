#!/usr/bin/env bash
set -Eeuo pipefail
# Apply ISO-X's Windows-inspired dark desktop preferences to a target HOME.
# This is an ISO-X cyber theme, not a pixel-exact copy of Windows.
TARGET_HOME="${1:-${ISOX_TARGET_HOME:-${HOME:?HOME is not set}}}"
TARGET_HOME="$(realpath -m "$TARGET_HOME")"
[[ -d "$TARGET_HOME" ]] || { echo "Target home is not a directory: $TARGET_HOME" >&2; exit 2; }
mkdir -p \
  "$TARGET_HOME/.config/gtk-3.0" \
  "$TARGET_HOME/.config/pcmanfm/isox" \
  "$TARGET_HOME/.config/libfm" \
  "$TARGET_HOME/.config/openbox" \
  "$TARGET_HOME/سطح المكتب" \
  "$TARGET_HOME/التنزيلات" \
  "$TARGET_HOME/المستندات" \
  "$TARGET_HOME/الصور" \
  "$TARGET_HOME/الفيديوهات" \
  "$TARGET_HOME/الموسيقى" \
  "$TARGET_HOME/القوالب" \
  "$TARGET_HOME/العامة"

cat > "$TARGET_HOME/.config/gtk-3.0/settings.ini" <<'EOF'
[Settings]
gtk-theme-name=Adwaita-dark
gtk-icon-theme-name=Adwaita
gtk-cursor-theme-name=DMZ-White
gtk-cursor-theme-size=32
gtk-font-name=Noto Sans Arabic 10
gtk-application-prefer-dark-theme=1
gtk-enable-primary-paste=1
gtk-xft-antialias=1
gtk-xft-hinting=1
gtk-xft-hintstyle=hintslight
EOF

cat > "$TARGET_HOME/.config/gtk-3.0/gtk.css" <<'EOF'
/* ISO-X cyber dark palette — GTK 3 only. */
@define-color theme_bg_color #0b101b;
@define-color theme_base_color #101725;
@define-color theme_fg_color #eaf4ff;
@define-color theme_text_color #eaf4ff;
@define-color theme_selected_bg_color #0078d4;
@define-color theme_selected_fg_color #ffffff;
@define-color accent_color #00c8ff;
window, dialog { background-color: @theme_bg_color; color: @theme_fg_color; }
button:focus, entry:focus, treeview.view:focus { outline-color: @accent_color; }
button:hover { border-color: @accent_color; }
selection, *:selected { background-color: @theme_selected_bg_color; color: @theme_selected_fg_color; }
menu, menuitem, popover, popover.background {
  background-color: #050812;
  color: #ffffff;
}
menuitem:hover, menuitem:selected {
  background-color: #0078d4;
  color: #ffffff;
}
menuitem:disabled { color: #aab4c4; }
EOF

cat > "$TARGET_HOME/.gtkrc-2.0" <<'EOF'
style "isox-menu" {
  bg[NORMAL] = "#050812"
  fg[NORMAL] = "#ffffff"
  bg[PRELIGHT] = "#0078d4"
  fg[PRELIGHT] = "#ffffff"
  bg[SELECTED] = "#0078d4"
  fg[SELECTED] = "#ffffff"
  bg[ACTIVE] = "#101725"
  fg[ACTIVE] = "#ffffff"
  bg[INSENSITIVE] = "#050812"
  fg[INSENSITIVE] = "#aab4c4"
}
widget_class "*Menu*" style "isox-menu"
widget_class "*MenuItem*" style "isox-menu"
EOF

cat > "$TARGET_HOME/.config/libfm/libfm.conf" <<'EOF'
[config]
single_click=1
use_trash=1
confirm_del=1
confirm_trash=1
EOF

cat > "$TARGET_HOME/.config/pcmanfm/isox/desktop-items-0.conf" <<'EOF'
[*]
wallpaper=/usr/share/backgrounds/iso-x/iso-x-desktop-wallpaper.png
wallpaper_mode=stretch
wallpaper_common=1
desktop_bg=#050812
desktop_fg=#eaf4ff
desktop_shadow=#000000
desktop_font=Noto Sans Arabic 10
show_wm_menu=0
sort=name
show_documents=1
show_trash=1
show_mounts=1
EOF

cat > "$TARGET_HOME/.config/user-dirs.dirs" <<'EOF'
XDG_DESKTOP_DIR="$HOME/سطح المكتب"
XDG_DOWNLOAD_DIR="$HOME/التنزيلات"
XDG_TEMPLATES_DIR="$HOME/القوالب"
XDG_PUBLICSHARE_DIR="$HOME/العامة"
XDG_DOCUMENTS_DIR="$HOME/المستندات"
XDG_MUSIC_DIR="$HOME/الموسيقى"
XDG_PICTURES_DIR="$HOME/الصور"
XDG_VIDEOS_DIR="$HOME/الفيديوهات"
EOF
printf '%s\n' 'ar_IQ' > "$TARGET_HOME/.config/user-dirs.locale"

# User configs should remain owned by the target account on a live desktop.
if [[ "$TARGET_HOME" == /etc/skel* ]]; then
  chmod 0644 "$TARGET_HOME/.config/gtk-3.0/settings.ini" \
    "$TARGET_HOME/.config/gtk-3.0/gtk.css" \
    "$TARGET_HOME/.gtkrc-2.0" \
    "$TARGET_HOME/.config/pcmanfm/isox/desktop-items-0.conf" \
    "$TARGET_HOME/.config/libfm/libfm.conf" \
    "$TARGET_HOME/.config/user-dirs.dirs" "$TARGET_HOME/.config/user-dirs.locale"
fi
printf 'ISO-X look settings written to: %s\n' "$TARGET_HOME"
