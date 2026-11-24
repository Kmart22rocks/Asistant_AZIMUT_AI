#include "MainWindow.h"
#include <QApplication>
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QGuiApplication>
#include <QScreen>
#include <QEvent>
#include <QCloseEvent>
#include <QTextCursor>
#include <QJsonObject>
#include <QJsonArray>

#ifdef Q_OS_WIN
#include <windows.h>
#endif

MainWindow::MainWindow(QWidget* parent)
    : QMainWindow(parent),
      m_thinkingTimer(new QTimer(this)),
      m_syncTimer(new QTimer(this)),
      m_thinkingDots(1),
      m_isThinking(false),
      m_procManager(new ProcessManager(this)),
      m_kompasBridge(new KompasBridge(this)),
      m_ollamaClient(new OllamaClient(this)),
      m_isConnected(false),
      m_isConnecting(false),
      m_inactiveOpacity(0.65) {

    setWindowTitle("АЗИМУТ — Персональный ИИ-ассистент (Alt+A)");
    setWindowFlags(Qt::Window | Qt::WindowStaysOnTopHint);
    resize(460, 620);

    setupUi();
    applyLightTheme();
    positionWindowTopRight();

    qApp->installNativeEventFilter(this);
#ifdef Q_OS_WIN
    RegisterHotKey(nullptr, 101, MOD_ALT, 'A');
#endif

    connect(m_thinkingTimer, &QTimer::timeout, this, &MainWindow::onThinkingTick);

    connect(m_syncTimer, &QTimer::timeout, this, [this]() {
        if (!m_isThinking && !m_isConnecting) {
            m_kompasBridge->checkStatus();
        }
    });

    connect(m_procManager, &ProcessManager::pythonServerReady, this, [this]() {
        m_isConnecting = true;
        m_statusIndicator->setState(StatusIndicator::State::BlinkingBlue);
        m_statusLabel->setText("Подключение к КОМПАС-3D...");
        m_kompasBridge->connectKompas();
        m_syncTimer->start(2500);
    });

    connect(m_kompasBridge, &KompasBridge::statusReceived, this, &MainWindow::onKompasStatusUpdated);
    connect(m_kompasBridge, &KompasBridge::executionFinished, this, &MainWindow::onExecutionFinished);
    connect(m_kompasBridge, &KompasBridge::contextUpdated, m_ollamaClient, &OllamaClient::updateContext);

    connect(m_kompasBridge, &KompasBridge::contextUpdated, this, [this](const QJsonArray& features, const QJsonObject& sel, const QJsonArray& tree) {
        int faces = sel.value("selected_faces").toInt();
        int edges = sel.value("selected_edges").toInt();
        m_selectionInfoLabel->setText(
            QString("Операций ИИ: %1 | В дереве: %2 | Выделено граней: %3, ребер: %4")
                .arg(features.size()).arg(tree.size()).arg(faces).arg(edges)
        );
    });

    connect(m_kompasBridge, &KompasBridge::bridgeError, this, [this](const QString& err) {
        m_isConnecting = false;
        m_isConnected = false;
        m_statusIndicator->setState(StatusIndicator::State::Red);
        m_statusLabel->setText("Отключено");
        m_connectBtn->setText("Подключить");
        if (m_isThinking) {
            stopThinkingAnimation("Ошибка связи с сервером КОМПАС-3D: " + err);
        } else {
            appendChatMessage("Система", err, "#C62828");
        }
    });

    connect(m_ollamaClient, &OllamaClient::clarificationNeeded, this, [this](const QString& question) {
        stopThinkingAnimation(question);
    });

    connect(m_ollamaClient, &OllamaClient::commandsReady, this, [this](const QString& replyText, const QJsonObject& payload) {
        stopThinkingAnimation(replyText);
        m_kompasBridge->executeCommands(payload);
    });

    connect(m_ollamaClient, &OllamaClient::errorOccurred, this, [this](const QString& err) {
        stopThinkingAnimation("Ошибка ИИ: " + err);
    });

    m_statusIndicator->setState(StatusIndicator::State::BlinkingBlue);
    m_statusLabel->setText("Запуск служб...");
    m_procManager->startServices();
}

MainWindow::~MainWindow() {
    qApp->removeNativeEventFilter(this);
#ifdef Q_OS_WIN
    UnregisterHotKey(nullptr, 101);
#endif
}

void MainWindow::toggleWindowVisibility() {
    if (!isVisible() || isMinimized()) {
        showNormal();
        raise();
        activateWindow();
        setWindowOpacity(1.0);
        m_inputEdit->setFocus();
    } else {
        hide();
    }
}

bool MainWindow::nativeEventFilter(const QByteArray& eventType, void* message, qintptr* result) {
    Q_UNUSED(result);
#ifdef Q_OS_WIN
    if (eventType == "windows_generic_MSG") {
        MSG* msg = static_cast<MSG*>(message);
        if (msg->message == WM_HOTKEY && msg->wParam == 101) {
            toggleWindowVisibility();
            return true;
        }
    }
#endif
    return false;
}

void MainWindow::setupUi() {
    QWidget* central = new QWidget(this);
    QVBoxLayout* mainLayout = new QVBoxLayout(central);
    mainLayout->setContentsMargins(10, 10, 10, 10);
    mainLayout->setSpacing(6);

    QHBoxLayout* topBar = new QHBoxLayout();
    m_statusIndicator = new StatusIndicator(this);
    m_statusLabel = new QLabel("Отключено", this);
    m_undoBtn = new QPushButton("Шаг назад", this);
    m_connectBtn = new QPushButton("Подключить", this);

    topBar->addWidget(m_statusIndicator);
    topBar->addWidget(m_statusLabel, 1);
    topBar->addWidget(m_undoBtn);
    topBar->addWidget(m_connectBtn);

    m_selectionInfoLabel = new QLabel("Операций ИИ: 0 | В дереве: 0 | Выделено граней: 0, ребер: 0", this);
    m_selectionInfoLabel->setStyleSheet("color: #546E7A; font-size: 11px;");

    m_tabs = new QTabWidget(this);

    QWidget* chatTab = new QWidget(this);
    QVBoxLayout* chatLayout = new QVBoxLayout(chatTab);
    chatLayout->setContentsMargins(6, 6, 6, 6);

    m_chatView = new QTextEdit(this);
    m_chatView->setReadOnly(true);

    QHBoxLayout* inputLayout = new QHBoxLayout();
    m_inputEdit = new QLineEdit(this);
    m_inputEdit->setPlaceholderText("Опишите деталь или изменение (например: фаска 2 мм)...");
    m_sendBtn = new QPushButton("Отправить", this);

    inputLayout->addWidget(m_inputEdit, 1);
    inputLayout->addWidget(m_sendBtn);

    chatLayout->addWidget(m_chatView, 1);
    chatLayout->addLayout(inputLayout);

    QWidget* helpTab = new QWidget(this);
    QVBoxLayout* helpLayout = new QVBoxLayout(helpTab);
    QTextEdit* helpText = new QTextEdit(this);
    helpText->setReadOnly(true);
    helpText->setHtml(
        "<h3>Инструкция по работе с АЗИМУТ</h3>"
        "<p><b>Горячая клавиша:</b> Нажмите <b>Alt + A</b> для мгновенного показа или скрытия окна ассистента.</p>"
        "<p><b>1. Базовые тела:</b> Пластина, параллелепипед, куб, цилиндр, труба, многогранная призма, конус, шар, паз и произвольный 2D-профиль по точкам.</p>"
        "<p><b>2. Вырезы и отверстия:</b> Одиночное отверстие, 4 отверстия по углам (отступ от края по ГОСТ), отверстия по окружности (фланец), прямоугольный паз/вырез.</p>"
        "<p><b>3. Фаски и скругления:</b> Напишите <i>«сделай фаску 2 мм»</i> или <i>«скругление радиусом 3 мм»</i>. Если в КОМПАС-3D мышкой выделены конкретные ребра или грани — операция применится к ним.</p>"
        "<p><b>4. Построение на выбранной грани:</b> Выделите плоскую грань детали мышкой в КОМПАС-3D и напишите <i>«построй на этой грани цилиндр диаметром 20 и высотой 15»</i>.</p>"
        "<p><b>5. Управление историей:</b> Кнопка <b>«Шаг назад»</b> или команды <i>«отмени последний шаг»</i>, <i>«удали фаску»</i>, <i>«очисти деталь»</i>.</p>"
    );
    helpLayout->addWidget(helpText);

    QWidget* settingsTab = new QWidget(this);
    QVBoxLayout* settingsLayout = new QVBoxLayout(settingsTab);

    QLabel* modelLabel = new QLabel("Языковая модель ИИ (Ускорение Intel Arc XMX / Vulkan):", this);
    m_modelCombo = new QComboBox(this);
    m_modelCombo->addItem("Qwen 2.5 Coder 14B (Высокая точность, ~9 ГБ)", "qwen2.5-coder:14b");
    m_modelCombo->addItem("Qwen 2.5 Coder 7B (Быстрая, ~4.7 ГБ)", "qwen2.5-coder:7b");

    connect(m_modelCombo, &QComboBox::currentIndexChanged, this, [this](int index) {
        QString selectedModel = m_modelCombo->itemData(index).toString();
        m_ollamaClient->setModelName(selectedModel);
        appendChatMessage("Система", "Активная модель переключена на: " + selectedModel, "#1565C0");
    });

    QLabel* opacityLabel = new QLabel("Прозрачность окна в неактивном режиме (%):", this);
    m_opacitySlider = new QSlider(Qt::Horizontal, this);
    m_opacitySlider->setRange(30, 100);
    m_opacitySlider->setValue(65);

    connect(m_opacitySlider, &QSlider::valueChanged, this, [this](int val) {
        m_inactiveOpacity = val / 100.0;
    });

    settingsLayout->addWidget(modelLabel);
    settingsLayout->addWidget(m_modelCombo);
    settingsLayout->addSpacing(10);
    settingsLayout->addWidget(opacityLabel);
    settingsLayout->addWidget(m_opacitySlider);
    settingsLayout->addStretch(1);

    m_tabs->addTab(chatTab, "Чат");
    m_tabs->addTab(helpTab, "Инструкция");
    m_tabs->addTab(settingsTab, "Параметры");

    mainLayout->addLayout(topBar);
    mainLayout->addWidget(m_selectionInfoLabel);
    mainLayout->addWidget(m_tabs, 1);
    setCentralWidget(central);

    connect(m_sendBtn, &QPushButton::clicked, this, &MainWindow::onSendClicked);
    connect(m_inputEdit, &QLineEdit::returnPressed, this, &MainWindow::onSendClicked);
    connect(m_undoBtn, &QPushButton::clicked, this, &MainWindow::onUndoClicked);

    connect(m_connectBtn, &QPushButton::clicked, this, [this]() {
        if (m_isConnected) {
            m_kompasBridge->disconnectKompas();
        } else {
            m_isConnecting = true;
            m_statusIndicator->setState(StatusIndicator::State::BlinkingBlue);
            m_statusLabel->setText("Подключение к КОМПАС-3D...");
            m_kompasBridge->connectKompas();
        }
    });

    appendChatMessage("АЗИМУТ", "Здравствуйте! Я готов к моделированию в КОМПАС-3D. Опишите деталь или выберите грань/ребро в окне КОМПАС-3D.", "#1565C0");
}

void MainWindow::applyLightTheme() {
    setStyleSheet(
        "QMainWindow, QWidget { background-color: #F8F9FA; color: #212529; font-family: 'Segoe UI'; font-size: 13px; }"
        "QTextEdit, QLineEdit { background-color: #FFFFFF; border: 1px solid #CED4DA; border-radius: 6px; padding: 6px; color: #212529; }"
        "QPushButton { background-color: #1976D2; color: #FFFFFF; border: none; border-radius: 6px; padding: 6px 12px; font-weight: bold; }"
        "QPushButton:hover { background-color: #1565C0; }"
        "QPushButton:disabled { background-color: #90CAF9; }"
        "QTabWidget::pane { border: 1px solid #DEE2E6; border-radius: 6px; background: #FFFFFF; }"
        "QTabBar::tab { background: #E9ECEF; padding: 6px 14px; border-top-left-radius: 6px; border-top-right-radius: 6px; margin-right: 2px; }"
        "QTabBar::tab:selected { background: #FFFFFF; font-weight: bold; color: #1976D2; }"
    );
}

void MainWindow::positionWindowTopRight() {
    QScreen* screen = QGuiApplication::primaryScreen();
    if (screen) {
        QRect avail = screen->availableGeometry();
        int posX = avail.right() - width() - 15;
        int posY = avail.top() + 100;
        move(posX, posY);
    }
}

void MainWindow::appendChatMessage(const QString& sender, const QString& text, const QString& colorHex) {
    m_chatView->append(QString("<b style='color:%1;'>%2:</b> %3").arg(colorHex, sender, text));
}

void MainWindow::startThinkingAnimation() {
    m_isThinking = true;
    m_thinkingDots = 1;
    m_sendBtn->setEnabled(false);
    m_chatView->append("<b style='color:#1565C0;'>АЗИМУТ:</b> <i>Думает .</i>");
    m_thinkingTimer->start(350);
}

void MainWindow::onThinkingTick() {
    m_thinkingDots = (m_thinkingDots % 3) + 1;
    QString dots;
    for (int i = 0; i < m_thinkingDots; ++i) {
        dots += " .";
    }

    QTextCursor cursor = m_chatView->textCursor();
    cursor.movePosition(QTextCursor::End);
    cursor.movePosition(QTextCursor::StartOfBlock, QTextCursor::KeepAnchor);
    cursor.removeSelectedText();
    cursor.insertHtml(QString("<b style='color:#1565C0;'>АЗИМУТ:</b> <i>Думает%1</i>").arg(dots));
}

void MainWindow::stopThinkingAnimation(const QString& finalReply) {
    if (m_isThinking) {
        m_thinkingTimer->stop();
        m_isThinking = false;
        QTextCursor cursor = m_chatView->textCursor();
        cursor.movePosition(QTextCursor::End);
        cursor.movePosition(QTextCursor::StartOfBlock, QTextCursor::KeepAnchor);
        cursor.removeSelectedText();
        cursor.insertHtml(QString("<b style='color:#1565C0;'>АЗИМУТ:</b> %1").arg(finalReply));
    } else {
        appendChatMessage("АЗИМУТ", finalReply, "#1565C0");
    }
    m_sendBtn->setEnabled(true);
}

void MainWindow::onSendClicked() {
    QString text = m_inputEdit->text().trimmed();
    if (text.isEmpty() || m_isThinking) return;

    m_inputEdit->clear();
    appendChatMessage("Вы", text, "#2E7D32");
    startThinkingAnimation();
    m_ollamaClient->sendPrompt(text);
}

void MainWindow::onUndoClicked() {
    if (m_isThinking) return;
    QJsonObject cmd;
    cmd["action"] = "undo";
    QJsonArray arr;
    arr.append(cmd);
    QJsonObject payload;
    payload["commands"] = arr;
    m_kompasBridge->executeCommands(payload);
}

void MainWindow::onKompasStatusUpdated(bool connected, bool docOpen, const QString& docName, const QString& message) {
    m_isConnecting = false;
    m_isConnected = connected;
    if (!connected) {
        m_statusIndicator->setState(StatusIndicator::State::Red);
        m_statusLabel->setText("Отключено");
        m_connectBtn->setText("Подключить");
    } else if (connected && !docOpen) {
        m_statusIndicator->setState(StatusIndicator::State::Yellow);
        m_statusLabel->setText("КОМПАС открыт (нет 3D-детали)");
        m_connectBtn->setText("Отключить");
    } else {
        m_statusIndicator->setState(StatusIndicator::State::Green);
        m_statusLabel->setText(docName.isEmpty() ? "3D-деталь активна" : docName);
        m_connectBtn->setText("Отключить");
    }
    Q_UNUSED(message);
}

void MainWindow::onExecutionFinished(bool success, const QString& message, const QStringList& logs) {
    if (success) {
        for (const QString& l : logs) {
            appendChatMessage("КОМПАС-3D", l, "#00695C");
        }
    } else {
        appendChatMessage("Ошибка КОМПАС-3D", message, "#C62828");
    }
    m_kompasBridge->checkStatus();
}

bool MainWindow::event(QEvent* event) {
    if (event->type() == QEvent::WindowActivate) {
        setWindowOpacity(1.0);
    } else if (event->type() == QEvent::WindowDeactivate) {
        setWindowOpacity(m_inactiveOpacity);
    }
    return QMainWindow::event(event);
}

void MainWindow::closeEvent(QCloseEvent* event) {
    m_syncTimer->stop();
    m_procManager->stopServices();
    event->accept();
    qApp->quit();
}