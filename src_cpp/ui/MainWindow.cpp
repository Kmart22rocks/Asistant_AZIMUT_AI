#include "MainWindow.h"
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QEvent>
#include <QGuiApplication>
#include <QScreen>
#include <QTextCursor>
#include <QJsonArray>
#include <windows.h>

MainWindow::MainWindow(QWidget *parent)
    : QMainWindow(parent),
      m_procManager(new ProcessManager(this)),
      m_kompasBridge(new KompasBridge(this)),
      m_ollamaClient(new OllamaClient(this)),
      m_isConnected(false),
      m_thinkingTimer(new QTimer(this)),
      m_thinkingDots(1) {

    setWindowTitle("АЗИМУТ — Персональный ИИ-ассистент (Alt+A)");
    resize(460, 620);
    setWindowFlags(windowFlags() | Qt::WindowStaysOnTopHint);

    RegisterHotKey(reinterpret_cast<HWND>(winId()), 101, MOD_ALT, 'A');

    QScreen *screen = QGuiApplication::primaryScreen();
    if (screen) {
        QRect avail = screen->availableGeometry();
        int posX = avail.right() - width() - 15;
        int posY = avail.top() + 100;
        move(posX, posY);
    }

    setStyleSheet(
        "QMainWindow, QWidget { background-color: #F8F9FA; color: #212529; font-family: 'Segoe UI'; font-size: 13px; }"
        "QTextEdit, QLineEdit { background-color: #FFFFFF; border: 1px solid #CED4DA; border-radius: 6px; padding: 6px; }"
        "QPushButton { background-color: #0D6EFD; color: #FFFFFF; border: none; border-radius: 6px; padding: 6px 12px; font-weight: bold; }"
        "QPushButton:hover { background-color: #0B5ED7; }"
        "QTabWidget::pane { border: 1px solid #DEE2E6; background: #FFFFFF; }"
        "QTabBar::tab { background: #E9ECEF; padding: 6px 12px; border-top-left-radius: 4px; border-top-right-radius: 4px; margin-right: 2px; }"
        "QTabBar::tab:selected { background: #FFFFFF; font-weight: bold; }"
    );

    QWidget *central = new QWidget(this);
    QVBoxLayout *mainLayout = new QVBoxLayout(central);

    QHBoxLayout *topBar = new QHBoxLayout();
    m_indicator = new StatusIndicator(this);
    m_statusLabel = new QLabel("Запуск...", this);
    m_undoBtn = new QPushButton("Шаг назад", this);
    m_connectBtn = new QPushButton("Подключить", this);

    topBar->addWidget(m_indicator);
    topBar->addWidget(m_statusLabel);
    topBar->addStretch();
    topBar->addWidget(m_undoBtn);
    topBar->addWidget(m_connectBtn);
    mainLayout->addLayout(topBar);

    m_tabs = new QTabWidget(this);

    QWidget *chatTab = new QWidget(this);
    QVBoxLayout *chatLayout = new QVBoxLayout(chatTab);
    m_chatHistory = new QTextEdit(this);
    m_chatHistory->setReadOnly(true);

    QHBoxLayout *inputLayout = new QHBoxLayout();
    m_inputField = new QLineEdit(this);
    m_inputField->setPlaceholderText("Введите команду (вызов из КОМПАСа: Alt+A)...");
    m_sendBtn = new QPushButton("Отправить", this);
    inputLayout->addWidget(m_inputField);
    inputLayout->addWidget(m_sendBtn);

    chatLayout->addWidget(m_chatHistory);
    chatLayout->addLayout(inputLayout);

    m_tabs->addTab(chatTab, "Чат");
    m_tabs->addTab(new QWidget(this), "Инструкция");
    m_tabs->addTab(new QWidget(this), "Параметры");

    mainLayout->addWidget(m_tabs);
    setCentralWidget(central);

    connect(m_thinkingTimer, &QTimer::timeout, this, &MainWindow::onThinkingTick);
    connect(m_undoBtn, &QPushButton::clicked, this, &MainWindow::onUndoClicked);
    connect(m_connectBtn, &QPushButton::clicked, this, &MainWindow::onToggleConnect);
    connect(m_sendBtn, &QPushButton::clicked, this, &MainWindow::onSendMessage);
    connect(m_inputField, &QLineEdit::returnPressed, this, &MainWindow::onSendMessage);

    connect(m_kompasBridge, &KompasBridge::statusReceived, this, &MainWindow::onStatusUpdated);

    connect(m_kompasBridge, &KompasBridge::commandExecuted, this,
            [this](bool ok, const QString &msg, const QJsonObject &ctx) {
                if (ok) m_cadContext = ctx;
                m_chatHistory->append("<b>КОМПАС-3D:</b> " + msg);
            });

    connect(m_ollamaClient, &OllamaClient::clarificationNeeded, this, [this](const QString &q) {
        finishThinkingWithText("<b>АЗИМУТ:</b> " + q);
    });

    connect(m_ollamaClient, &OllamaClient::commandsReady, this,
            [this](const QString &reply, const QJsonObject &payload) {
                finishThinkingWithText("<b>АЗИМУТ:</b> " + reply);
                m_kompasBridge->sendCommand(payload);
            });

    connect(m_ollamaClient, &OllamaClient::errorOccurred, this, [this](const QString &err) {
        finishThinkingWithText("<span style='color:red;'><b>Ошибка:</b> " + err + "</span>");
    });

    m_chatHistory->append("<b>АЗИМУТ:</b> Запуск фоновых служб...");
    m_procManager->startServices();

    connect(m_procManager, &ProcessManager::pythonServerReady, this, [this]() {
        m_chatHistory->append("<b>АЗИМУТ:</b> Сервер готов. Открываю КОМПАС-3D...");
        onToggleConnect();
    });

    connect(m_syncTimer, &QTimer::timeout, this, [this]() {
    if (m_isConnected && !m_thinkingTimer->isActive()) {
        m_kompasBridge->checkStatus();
    }
});

    connect(m_procManager, &ProcessManager::pythonServerReady, this, [this]() {
        m_chatHistory->append("<b>АЗИМУТ:</b> Сервер готов. Открываю КОМПАС-3D...");
        onToggleConnect();
        m_syncTimer->start(2500);
    });
}

MainWindow::~MainWindow() {
    UnregisterHotKey(reinterpret_cast<HWND>(winId()), 101);
    m_procManager->stopServices();
}

bool MainWindow::nativeEvent(const QByteArray &eventType, void *message, qintptr *result) {
    if (eventType == "windows_generic_MSG") {
        MSG *msg = static_cast<MSG *>(message);
        if (msg->message == WM_HOTKEY && msg->wParam == 101) {
            toggleAssistantWindow();
            return true;
        }
    }
    return QMainWindow::nativeEvent(eventType, message, result);
}

void MainWindow::toggleAssistantWindow() {
    if (isMinimized() || !isVisible()) {
        showNormal();
        raise();
        activateWindow();
        m_inputField->setFocus();
    } else if (!isActiveWindow()) {
        raise();
        activateWindow();
        m_inputField->setFocus();
    } else {
        showMinimized();
    }
}

bool MainWindow::event(QEvent *event) {
    if (event->type() == QEvent::WindowActivate) {
        setWindowOpacity(1.0);
    } else if (event->type() == QEvent::WindowDeactivate) {
        setWindowOpacity(0.65);
    }
    return QMainWindow::event(event);
}

void MainWindow::startThinkingAnimation() {
    m_thinkingDots = 1;
    m_chatHistory->append("<b>АЗИМУТ:</b> Думает .");
    m_thinkingTimer->start(350);
}

void MainWindow::onThinkingTick() {
    m_thinkingDots = (m_thinkingDots % 3) + 1;
    QString dots;
    for (int i = 0; i < m_thinkingDots; ++i) {
        dots += (i == 0) ? "." : " .";
    }
    QTextCursor cursor(m_chatHistory->document());
    cursor.movePosition(QTextCursor::End);
    cursor.movePosition(QTextCursor::StartOfBlock, QTextCursor::KeepAnchor);
    cursor.removeSelectedText();
    cursor.insertHtml("<b>АЗИМУТ:</b> Думает " + dots);
}

void MainWindow::finishThinkingWithText(const QString &htmlText) {
    if (m_thinkingTimer->isActive()) {
        m_thinkingTimer->stop();
        QTextCursor cursor(m_chatHistory->document());
        cursor.movePosition(QTextCursor::End);
        cursor.movePosition(QTextCursor::StartOfBlock, QTextCursor::KeepAnchor);
        cursor.removeSelectedText();
        cursor.insertHtml(htmlText);
    } else {
        m_chatHistory->append(htmlText);
    }
}

void MainWindow::onToggleConnect() {
    if (!m_isConnected) {
        m_indicator->setState(StatusIndicator::BlinkingBlue);
        m_statusLabel->setText("Подключение к КОМПАС-3D...");
        QTimer::singleShot(400, m_kompasBridge, &KompasBridge::connectKompas);
    } else {
        m_kompasBridge->disconnectKompas();
    }
}

void MainWindow::onUndoClicked() {
    QJsonObject cmd;
    cmd["action"] = "undo";
    QJsonArray arr;
    arr.append(cmd);
    QJsonObject payload;
    payload["commands"] = arr;
    m_kompasBridge->sendCommand(payload);
}

void MainWindow::onStatusUpdated(const QString &indicator, const QString &text, const QJsonObject &context) {
    m_statusLabel->setText(text);
    if (!context.isEmpty()) {
        m_cadContext = context;
    }
    if (indicator == "green") {
        m_indicator->setState(StatusIndicator::Green);
        m_connectBtn->setText("Отключить");
        m_isConnected = true;
    } else if (indicator == "yellow") {
        m_indicator->setState(StatusIndicator::Yellow);
        m_connectBtn->setText("Отключить");
        m_isConnected = true;
    } else {
        m_indicator->setState(StatusIndicator::Red);
        m_connectBtn->setText("Подключить");
        m_isConnected = false;
    }
}

void MainWindow::onSendMessage() {
    QString text = m_inputField->text().trimmed();
    if (text.isEmpty() || m_thinkingTimer->isActive()) return;

    m_chatHistory->append("<b>Вы:</b> " + text);
    m_inputField->clear();
    startThinkingAnimation();

    QTimer::singleShot(50, this, [this, text]() {
        m_kompasBridge->checkStatus();
        QTimer::singleShot(150, this, [this, text]() {
            m_ollamaClient->askAgent(text, m_cadContext);
        });
    });
}