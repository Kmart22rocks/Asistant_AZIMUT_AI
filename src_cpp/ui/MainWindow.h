#pragma once
#include <QMainWindow>
#include <QAbstractNativeEventFilter>
#include <QTextEdit>
#include <QLineEdit>
#include <QPushButton>
#include <QLabel>
#include <QSlider>
#include <QComboBox>
#include <QTabWidget>
#include <QTimer>
#include "StatusIndicator.h"
#include "../core/ProcessManager.h"
#include "../network/KompasBridge.h"
#include "../network/OllamaClient.h"

class MainWindow : public QMainWindow, public QAbstractNativeEventFilter {
    Q_OBJECT
public:
    explicit MainWindow(QWidget* parent = nullptr);
    ~MainWindow() override;

    bool nativeEventFilter(const QByteArray& eventType, void* message, qintptr* result) override;

protected:
    bool event(QEvent* event) override;
    void closeEvent(QCloseEvent* event) override;

private slots:
    void onSendClicked();
    void onUndoClicked();
    void onKompasStatusUpdated(bool connected, bool docOpen, const QString& docName, const QString& message);
    void onExecutionFinished(bool success, const QString& message, const QStringList& logs);
    void onThinkingTick();

private:
    void setupUi();
    void applyLightTheme();
    void positionWindowTopRight();
    void toggleWindowVisibility();
    void appendChatMessage(const QString& sender, const QString& text, const QString& colorHex);
    void startThinkingAnimation();
    void stopThinkingAnimation(const QString& finalReply);

    StatusIndicator* m_statusIndicator;
    QLabel* m_statusLabel;
    QPushButton* m_undoBtn;
    QPushButton* m_connectBtn;
    QTabWidget* m_tabs;
    QTextEdit* m_chatView;
    QLineEdit* m_inputEdit;
    QPushButton* m_sendBtn;
    QSlider* m_opacitySlider;
    QComboBox* m_modelCombo;
    QLabel* m_selectionInfoLabel;

    QTimer* m_thinkingTimer;
    QTimer* m_syncTimer;
    int m_thinkingDots;
    bool m_isThinking;

    ProcessManager* m_procManager;
    KompasBridge* m_kompasBridge;
    OllamaClient* m_ollamaClient;
    bool m_isConnected;
    bool m_isConnecting;
    double m_inactiveOpacity;
};