#include "OllamaClient.h"
#include <QJsonDocument>
#include <QNetworkRequest>
#include <QUrl>
#include <QRegularExpression>

OllamaClient::OllamaClient(QObject *parent)
    : QObject(parent),
      m_nam(new QNetworkAccessManager(this)),
      m_baseUrl("http://127.0.0.1:11434"),
      m_modelName("qwen2.5-coder:14b"),
      m_isOnline(false)
{
    m_pingTimer = new QTimer(this);
    connect(m_pingTimer, &QTimer::timeout, this, &OllamaClient::checkConnection);
    m_pingTimer->start(3000);
    checkConnection();
}

void OllamaClient::setModelName(const QString &model) {
    m_modelName = model;
}

QString OllamaClient::modelName() const {
    return m_modelName;
}

void OllamaClient::clearHistory() {
    m_history = QJsonArray();
}

void OllamaClient::updateContext(const QJsonArray &features, const QJsonObject &selection, const QJsonArray &tree) {
    QJsonObject ctx;
    ctx["features"] = features;
    ctx["selection"] = selection;
    ctx["tree"] = tree;
    m_currentContext = ctx;
}

void OllamaClient::checkConnection() {
    QNetworkRequest req(QUrl(m_baseUrl + "/api/tags"));
    req.setTransferTimeout(1500);
    QNetworkReply *reply = m_nam->get(req);
    connect(reply, &QNetworkReply::finished, this, &OllamaClient::onCheckFinished);
}

void OllamaClient::onCheckFinished() {
    QNetworkReply *reply = qobject_cast<QNetworkReply*>(sender());
    if (!reply) return;

    bool ok = (reply->error() == QNetworkReply::NoError);
    if (ok != m_isOnline) {
        m_isOnline = ok;
        emit statusChanged(m_isOnline);
    }
    reply->deleteLater();
}

QString OllamaClient::buildSystemPrompt() const {
    return QString(
        "Ты — «АЗИМУТ», локальный ИИ-ассистент инженера-конструктора в САПР КОМПАС-3D.\n"
        "Общайся СТРОГО на русском языке. Отвечай кратко, точно и профессионально.\n"
        "Твой ответ ДОЛЖЕН быть СТРОГО в формате валидного JSON без лишнего текста:\n"
        "{\n"
        "  \"reply\": \"Текст ответа конструктору\",\n"
        "  \"commands\": [\n"
        "    {\n"
        "      \"action\": \"build | update | delete | clear_all | undo | ask\",\n"
        "      \"type\": \"plate | cylinder | tube | polygon | cone | sphere | torus | dome | hole | holes_corner | holes_circ | holes_grid | cut_box | slot | cross_slot | t_slot | counterbore | countersink | groove | chamfer | fillet | shell | shaft | rect_tube | l_profile | u_profile | i_beam | t_beam | spring | gear | flange | rib | bolt | nut | washer | screw | bearing | pin | key | appearance | profile\",\n"
        "      \"id\": \"уникальный_id\",\n"
        "      \"params\": {}\n"
        "    }\n"
        "  ]\n"
        "}\n"
        "ПРАВИЛА СИСТЕМЫ КООРДИНАТ КОМПАС-3D:\n"
        "1. Все построения начинаются на плоскости XOZ (y_offset = 0). Первая деталь ВСЕГДА центрируется в (0, 0) (x: 0, z: 0, y_offset: 0).\n"
        "2. Ось Y вертикальная: Вверх = +Y (direction: 1, y_offset > 0), Вниз = -Y (direction: -1, y_offset < 0).\n"
        "3. На плоскости XOZ: Вправо = -Z (z < 0), Влево = +Z (z > 0), Вперёд = -X (x < 0), Назад = +X (x > 0).\n"
        "4. Для построения на верхней грани существующей фигуры передавай base: \"top\" и direction: 1; на нижней грани — base: \"bottom\" и direction: -1.\n"
        "5. Отверстия по углам (holes_corner): считаются автоматически от краёв плиты (width, length, d, offset).\n"
        "6. Угол уклона (angle): > 0 расширяет наружу, < 0 сужает внутрь.\n"
        "7. СТРОГИЙ АЛГОРИТМ ДЛЯ СТАНДАРТНЫХ ИЗДЕЛИЙ (bolt, nut, washer, screw, bearing, pin, key):\n"
        "   Последовательность СТРОГО: Принять запрос -> Запросить ГОСТ -> Запросить недостающие размеры -> Построить модель.\n"
        "   ВАЖНО: Обозначение М<число> (например, М24, M12) УЖЕ задаёт диаметр d (М24 -> d: 24). Обозначение М24х180 УЖЕ задаёт d: 24 и length: 180. Никогда не переспрашивай диаметр d, если было указано М<число>!\n"
        "   - Шаг 1: Если пользователь просит стандартное изделие и ещё НЕ выбрал ГОСТ, НЕ СТРОЙ (action: \"ask\"). Выведи список ГОСТов:\n"
        "     * bolt (Болт): ГОСТ 7798-70 (нормальная головка), ГОСТ 7796-70 (уменьшенная головка), ГОСТ 7808-70 (повышенной точности).\n"
        "     * nut (Гайка): ГОСТ 5915-70 (нормальная), ГОСТ 5916-70 (низкая), ГОСТ 15521-70 (уменьшенная под ключ).\n"
        "     * washer (Шайба): ГОСТ 11371-78 (нормальная), ГОСТ 6958-78 (увеличенная), ГОСТ 10450-78 (уменьшенная).\n"
        "     * screw (Винт): ГОСТ 11738-84 (внутренний шестигранник), ГОСТ 1491-80 (цилиндрическая головка и шлиц), ГОСТ 17475-80 (потайная головка).\n"
        "     * bearing (Подшипник): ГОСТ 8338-75 (шариковый радиальный), ГОСТ 7242-81 (с защитными шайбами), ГОСТ 8328-75 (роликовый радиальный).\n"
        "     * pin (Штифт): ГОСТ 3128-70 (цилиндрический незакаленный), ГОСТ 24296-93 (цилиндрический закаленный), ГОСТ 3129-70 (конический).\n"
        "     * key (Шпонка): ГОСТ 23360-78 (скругленные торцы), ГОСТ 23360-78 исп. 2 (плоские торцы), ГОСТ 24071-97 (сегментная).\n"
        "   - Шаг 2: Когда ГОСТ выбран, проверь только НЕДОСТАЮЩИЕ параметры (bolt/screw/pin: d и length; nut/washer: d; bearing: d, D, B; key: b, h, length). Если чего-то нет — отправь action: \"ask\".\n"
        "   - Шаг 3: Когда известны gost и размеры — отправь action: \"build\"."
    );
}

void OllamaClient::sendPrompt(const QString &userPrompt) {
    m_lastUserPrompt = userPrompt;
    QString kompasContext = QString::fromUtf8(QJsonDocument(m_currentContext).toJson(QJsonDocument::Compact));

    QNetworkRequest req(QUrl(m_baseUrl + "/api/chat"));
    req.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");
    req.setTransferTimeout(120000);

    QJsonArray messages;
    QJsonObject sysMsg;
    sysMsg["role"] = "system";
    sysMsg["content"] = buildSystemPrompt();
    messages.append(sysMsg);

    for (const QJsonValue &val : m_history) {
        messages.append(val);
    }

    QJsonObject userMsg;
    userMsg["role"] = "user";
    userMsg["content"] = QString("КОНТЕКСТ ДЕТАЛИ:\n%1\n\nЗАПРОС КОНСТРУКТОРА:\n%2").arg(kompasContext, userPrompt);
    messages.append(userMsg);

    QJsonObject payload;
    payload["model"] = m_modelName;
    payload["messages"] = messages;
    payload["stream"] = false;
    payload["format"] = "json";

    QJsonObject options;
    options["temperature"] = 0.1;
    options["num_ctx"] = 4096;
    payload["options"] = options;

    QNetworkReply *reply = m_nam->post(req, QJsonDocument(payload).toJson(QJsonDocument::Compact));
    connect(reply, &QNetworkReply::finished, this, &OllamaClient::onReplyFinished);
}

static QString gostPromptForType(const QString &type) {
    if (type == "bolt")
        return "Выберите ГОСТ для построения болта:\n1. ГОСТ 7798-70 — с шестигранной головкой (нормальной точности)\n2. ГОСТ 7796-70 — с уменьшенной шестигранной головкой\n3. ГОСТ 7808-70 — с шестигранной головкой повышенной точности";
    if (type == "nut")
        return "Выберите ГОСТ для построения гайки:\n1. ГОСТ 5915-70 — шестигранная нормальная\n2. ГОСТ 5916-70 — шестигранная низкая\n3. ГОСТ 15521-70 — шестигранная с уменьшенным размером под ключ";
    if (type == "washer")
        return "Выберите ГОСТ для построения шайбы:\n1. ГОСТ 11371-78 — плоская нормальная\n2. ГОСТ 6958-78 — плоская увеличенная\n3. ГОСТ 10450-78 — плоская уменьшенная";
    if (type == "screw")
        return "Выберите ГОСТ для построения винта:\n1. ГОСТ 11738-84 — с цилиндрической головкой и внутренним шестигранником\n2. ГОСТ 1491-80 — с цилиндрической головкой и прямым шлицем\n3. ГОСТ 17475-80 — с потайной головкой";
    if (type == "bearing")
        return "Выберите ГОСТ для построения подшипника:\n1. ГОСТ 8338-75 — шариковый радиальный однорядный\n2. ГОСТ 7242-81 — шариковый радиальный с защитными шайбами\n3. ГОСТ 8328-75 — роликовый радиальный";
    if (type == "pin")
        return "Выберите ГОСТ для построения штифта:\n1. ГОСТ 3128-70 — цилиндрический незакаленный\n2. ГОСТ 24296-93 — цилиндрический закаленный\n3. ГОСТ 3129-70 — конический";
    if (type == "key")
        return "Выберите ГОСТ для построения шпонки:\n1. ГОСТ 23360-78 — призматическая со скругленными торцами\n2. ГОСТ 23360-78 исп. 2 — призматическая с плоскими торцами\n3. ГОСТ 24071-97 — сегментная";
    return "Укажите ГОСТ для стандартного изделия.";
}

void OllamaClient::onReplyFinished() {
    QNetworkReply *reply = qobject_cast<QNetworkReply*>(sender());
    if (!reply) return;

    if (reply->error() != QNetworkReply::NoError) {
        emit errorOccurred("Ошибка связи с ИИ (Ollama): " + reply->errorString());
        reply->deleteLater();
        return;
    }

    QByteArray rawData = reply->readAll();
    reply->deleteLater();

    QJsonDocument outerDoc = QJsonDocument::fromJson(rawData);
    if (!outerDoc.isObject()) {
        emit errorOccurred("Некорректный ответ от сервера Ollama.");
        return;
    }

    QString content = outerDoc.object().value("message").toObject().value("content").toString().trimmed();

    QJsonParseError err;
    QJsonDocument innerDoc = QJsonDocument::fromJson(content.toUtf8(), &err);
    if (err.error != QJsonParseError::NoError || !innerDoc.isObject()) {
        QRegularExpression rx("\\{[\\s\\S]*\\}");
        QRegularExpressionMatch match = rx.match(content);
        if (match.hasMatch()) {
            innerDoc = QJsonDocument::fromJson(match.captured(0).toUtf8(), &err);
        }
    }

    if (!innerDoc.isObject()) {
        emit clarificationNeeded(content);
        return;
    }

    QString dialogText;
    for (const QJsonValue &hVal : m_history) {
        if (hVal.isObject() && hVal.toObject().value("role").toString() == "user") {
            dialogText += " " + hVal.toObject().value("content").toString();
        }
    }
    dialogText += " " + m_lastUserPrompt;

    QRegularExpression metricRx("(?:^|\\s)[МмMm]\\s*(\\d+(?:[.,]\\d+)?)(?:\\s*[xхXХ*]\\s*(\\d+(?:[.,]\\d+)?))?");
    QRegularExpressionMatch metricMatch = metricRx.match(dialogText);

    QRegularExpression gostRx("(\\d{4,5}-\\d{2})");
    QRegularExpressionMatch gostMatch = gostRx.match(dialogText);

    QString detectedStdType;
    QString lowerDialog = dialogText.toLower();
    if (lowerDialog.contains("болт")) detectedStdType = "bolt";
    else if (lowerDialog.contains("гайк")) detectedStdType = "nut";
    else if (lowerDialog.contains("шайб")) detectedStdType = "washer";
    else if (lowerDialog.contains("винт")) detectedStdType = "screw";
    else if (lowerDialog.contains("подшипник")) detectedStdType = "bearing";
    else if (lowerDialog.contains("штифт")) detectedStdType = "pin";
    else if (lowerDialog.contains("шпонк")) detectedStdType = "key";

    QJsonObject obj = innerDoc.object();
    QString replyText = obj.value("reply").toString("Готово.");
    QJsonArray commands = obj.value("commands").toArray();

    if (commands.isEmpty() && !detectedStdType.isEmpty()) {
        QJsonObject syntheticCmd;
        syntheticCmd["action"] = "ask";
        syntheticCmd["type"] = detectedStdType;
        syntheticCmd["id"] = detectedStdType + "_1";
        syntheticCmd["params"] = QJsonObject();
        commands.append(syntheticCmd);
    }

    QJsonArray executableCommands;
    bool needsAsk = false;
    const QStringList stdTypes = {"bolt", "nut", "washer", "screw", "bearing", "pin", "key", "standard_part"};

    for (const QJsonValue &val : commands) {
        if (!val.isObject()) continue;
        QJsonObject cmd = val.toObject();
        QString action = cmd.value("action").toString("build");
        QString type = cmd.value("type").toString();
        if (type == "standard_part" && !detectedStdType.isEmpty()) {
            type = detectedStdType;
            cmd["type"] = type;
        }
        QJsonObject params = cmd.value("params").toObject();

        if (stdTypes.contains(type)) {
            if (metricMatch.hasMatch()) {
                if (!params.contains("d") && !params.contains("diameter")) {
                    params["d"] = metricMatch.captured(1).replace(',', '.').toDouble();
                }
                if (!metricMatch.captured(2).isEmpty() && !params.contains("length") && !params.contains("height")) {
                    params["length"] = metricMatch.captured(2).replace(',', '.').toDouble();
                }
            }
            if (params.value("gost").toString().trimmed().isEmpty() && gostMatch.hasMatch()) {
                params["gost"] = "ГОСТ " + gostMatch.captured(1);
            }
            cmd["params"] = params;

            QString gost = params.value("gost").toString().trimmed();
            if (gost.isEmpty()) {
                needsAsk = true;
                replyText = gostPromptForType(type);
                continue;
            }

            QStringList missing;
            if (type == "bolt" || type == "screw" || type == "pin") {
                if (!params.contains("d") && !params.contains("diameter")) missing << "диаметр (d)";
                if (!params.contains("length") && !params.contains("height")) missing << "длину (length)";
            } else if (type == "nut" || type == "washer") {
                if (!params.contains("d") && !params.contains("diameter")) missing << "диаметр (d)";
            } else if (type == "bearing") {
                if (!params.contains("d")) missing << "внутренний диаметр (d)";
                if (!params.contains("D")) missing << "наружный диаметр (D)";
                if (!params.contains("B") && !params.contains("width") && !params.contains("length")) missing << "ширину (B)";
            } else if (type == "key") {
                if (!params.contains("b") && !params.contains("width")) missing << "ширину (b)";
                if (!params.contains("h") && !params.contains("height")) missing << "высоту (h)";
                if (!params.contains("length")) missing << "длину (length)";
            }

            if (!missing.isEmpty()) {
                needsAsk = true;
                replyText = QString("Выбран %1. Укажите недостающие параметры: %2.").arg(gost, missing.join(", "));
                continue;
            }

            cmd["action"] = "build";
            executableCommands.append(cmd);
            continue;
        }

        if (action == "ask" || action == "none") {
            needsAsk = true;
            continue;
        }

        executableCommands.append(cmd);
    }

    if (needsAsk || executableCommands.isEmpty()) {
        QJsonObject uMsg;
        uMsg["role"] = "user";
        uMsg["content"] = m_lastUserPrompt;
        m_history.append(uMsg);

        QJsonObject aMsg;
        aMsg["role"] = "assistant";
        aMsg["content"] = replyText;
        m_history.append(aMsg);

        while (m_history.size() > 6) {
            m_history.removeFirst();
        }

        emit clarificationNeeded(replyText);
    } else {
        m_history = QJsonArray();
        QJsonObject outPayload;
        outPayload["commands"] = executableCommands;
        emit commandsReady(replyText, outPayload);
    }
}