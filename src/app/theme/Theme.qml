pragma Singleton
import QtQuick

QtObject {
    readonly property var colors: ({
        slate: { 50: "#F8FAFC", 100: "#F1F5F9", 200: "#E2E8F0", 400: "#94A3B8", 500: "#64748B", 600: "#475569", 700: "#334155", 800: "#1E293B", 900: "#0F172A" },
        blue: { 100: "#DBEAFE", 300: "#93C5FD", 400: "#60A5FA", 500: "#3B82F6", 600: "#2563EB", 700: "#1D4ED8" },
        violet: { 50: "#F5F3FF", 100: "#EDE9FE", 300: "#C4B5FD", 500: "#8B5CF6", 600: "#7C3AED", 700: "#6D28D9" },
        green: { 500: "#16A34A", 600: "#10B981" },
        amber: { 500: "#F59E0B", 600: "#D97706" },
        red: { 500: "#EF4444", 600: "#DC2626" },
        cyan: { 500: "#0EA5E9" },
        white: "#FFFFFF"
    })

    readonly property var space: ({ "1": 4, "2": 8, "2.5": 10, "3": 12, "4": 16 })
    readonly property var radii: ({ xs: 4, sm: 6, md: 8, lg: 10, xl: 12 })
    readonly property var fontFamily: ({
        ui: Qt.application.font.family,
        mono: Qt.platform.os === "osx" ? "Menlo" : "Consolas"
    })
    readonly property var fontSize: ({ title: 20, heading: 15, body: 13, mono: 12, nav: 13, caption: 11 })

    readonly property var tokensLight: ({
        "color-bg-page": "#F8FAFC",
        "color-bg-surface": "#FFFFFF",
        "color-bg-subtle": "#EEF2F7",
        "color-bg-subtle-2": "#F8FAFC",
        "color-border-default": "#C7D2E0",
        "color-text-primary": "#333333",
        "color-text-regular": "#333333",
        "color-text-secondary": "#94A3B8",
        "color-primary": "#8B5CF6",
        "color-primary-hover": "#C4B5FD",
        "color-primary-active": "#7C3AED",
        "color-primary-bg": "#F5F3FF",
        "color-success": "#10B981",
        "color-warning": "#F59E0B",
        "color-danger": "#EF4444",
        "color-info": "#0EA5E9",
        "color-nav-idle": "#334155",
        "color-nav-active-bg": "#EDE9FE",
        "color-nav-item-active-bg": "#F5F3FF",
        "color-nav-active-text": "#6D28D9",
        "color-nav-icon-idle-bg": "#F1F5F9",
        "color-nav-icon-active-bg": "#C4B5FD",
        "color-nav-icon-active-bg-soft": "#EDE9FE",
        "color-method-get": "#16A34A",
        "color-method-post": "#F59E0B",
        "color-method-put": "#3B82F6",
        "color-method-delete": "#EF4444",
        "color-method-patch": "#0EA5E9",
        "color-table-header": "#FAFAFB",
        "color-row-hover": "#F8F8FA",
        "color-status-bar-bg": "#F7F7F8"
    })

    readonly property var tokensDark: ({
        "color-bg-page": "#0F172A",
        "color-bg-surface": "#111827",
        "color-bg-subtle": "#121C2F",
        "color-bg-subtle-2": "#111827",
        "color-border-default": "#3A4658",
        "color-text-primary": "#F8FAFC",
        "color-text-regular": "#CBD5E1",
        "color-text-secondary": "#94A3B8",
        "color-primary": "#8B5CF6",
        "color-primary-hover": "#C4B5FD",
        "color-primary-active": "#7C3AED",
        "color-primary-bg": "#1A1535",
        "color-success": "#10B981",
        "color-warning": "#F59E0B",
        "color-danger": "#EF4444",
        "color-info": "#0EA5E9",
        "color-nav-idle": "#94A3B8",
        "color-nav-active-bg": "#6D28D9",
        "color-nav-item-active-bg": "#1A1535",
        "color-nav-active-text": "#EDE9FE",
        "color-nav-icon-idle-bg": "#1E293B",
        "color-nav-icon-active-bg": "#7C3AED",
        "color-nav-icon-active-bg-soft": "#231840",
        "color-method-get": "#22C55E",
        "color-method-post": "#FBBF24",
        "color-method-put": "#60A5FA",
        "color-method-delete": "#F87171",
        "color-method-patch": "#22D3EE",
        "color-table-header": "#0F1623",
        "color-row-hover": "#15202E",
        "color-status-bar-bg": "#0F1623"
    })

    function token(name, darkMode) {
        return (darkMode ? tokensDark : tokensLight)[name]
    }
}
