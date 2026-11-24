#include <windows.h>
#include <string>

extern "C" {

__declspec(dllexport) const char* __stdcall LIBRARYNAME() {
    return "AZIMUT AI Assistant";
}

__declspec(dllexport) void __stdcall LIBRARYENTRY(unsigned int) {
    HWND hwnd = FindWindowW(nullptr, L"АЗИМУТ — Персональный ИИ-ассистент (Alt+A)");
    if (hwnd) {
        if (IsIconic(hwnd)) {
            ShowWindow(hwnd, SW_RESTORE);
        } else {
            ShowWindow(hwnd, SW_SHOW);
        }
        SetForegroundWindow(hwnd);
        return;
    }

    const wchar_t *qtPath = L"D:\\Qt-data\\6.12.0\\mingw_64\\bin;D:\\Qt-data\\Tools\\mingw1310_64\\bin;";
    wchar_t oldPath[32767];
    GetEnvironmentVariableW(L"PATH", oldPath, 32767);
    std::wstring newPath = std::wstring(qtPath) + oldPath;
    SetEnvironmentVariableW(L"PATH", newPath.c_str());

    const wchar_t *exePath = L"D:\\Projects file\\CLionProjects\\Asistant_AZIMUT_II\\cmake-build-debug\\Asistant_AZIMUT_II.exe";
    const wchar_t *workDir = L"D:\\Projects file\\CLionProjects\\Asistant_AZIMUT_II\\cmake-build-debug";

    STARTUPINFOW si = { sizeof(si) };
    PROCESS_INFORMATION pi = {};
    if (CreateProcessW(exePath, nullptr, nullptr, nullptr, FALSE, 0, nullptr, workDir, &si, &pi)) {
        CloseHandle(pi.hProcess);
        CloseHandle(pi.hThread);
    }
}

}