#include "OllamaClient.h"
#include <QJsonDocument>
#include <QNetworkRequest>
#include <QUrl>
#include <QRegularExpression>

static QString sanitizeText(QString text) {
    return text.replace(QString::fromUtf8("—"), "-")
               .replace(QString::fromUtf8("–"), "-")
               .replace(QString::fromUtf8("−"), "-")
               .replace(QString::fromUtf8("«"), "\"")
               .replace(QString::fromUtf8("»"), "\"")
               .replace(QString::fromUtf8("“"), "\"")
               .replace(QString::fromUtf8("”"), "\"");
}

static QString gostPromptForType(const QString &type) {
    if (type == "bolt")
        return "Выберите ГОСТ для построения болта:\n1. ГОСТ 7798-70 - с шестигранной головкой (нормальной точности)\n2. ГОСТ 7796-70 - с уменьшенной шестигранной головкой\n3. ГОСТ 7808-70 - с шестигранной головкой повышенной точности";
    if (type == "nut")
        return "Выберите ГОСТ для построения гайки:\n1. ГОСТ 5915-70 - шестигранная нормальная\n2. ГОСТ 5916-70 - шестигранная низкая\n3. ГОСТ 15521-70 - шестигранная с уменьшенным размером под ключ";
    if (type == "washer")
        return "Выберите ГОСТ для построения шайбы:\n1. ГОСТ 11371-78 - плоская нормальная\n2. ГОСТ 6958-78 - плоская увеличенная\n3. ГОСТ 10450-78 - плоская уменьшенная";
    if (type == "screw")
        return "Выберите ГОСТ для построения винта:\n1. ГОСТ 11738-84 - с цилиндрической головкой и внутренним шестигранником\n2. ГОСТ 1491-80 - с цилиндрической головкой и прямым шлицем\n3. ГОСТ 17475-80 - с потайной головкой";
    if (type == "bearing")
        return "Выберите ГОСТ для построения подшипника:\n1. ГОСТ 8338-75 - шариковый радиальный однорядный\n2. ГОСТ 7242-81 - шариковый радиальный с защитными шайбами\n3. ГОСТ 8328-75 - роликовый радиальный";
    if (type == "pin")
        return "Выберите ГОСТ для построения штифта:\n1. ГОСТ 3128-70 - цилиндрический незакаленный\n2. ГОСТ 24296-93 - цилиндрический закаленный\n3. ГОСТ 3129-70 - конический";
    if (type == "key")
        return "Выберите ГОСТ для построения шпонки:\n1. ГОСТ 23360-78 - призматическая со скругленными торцами\n2. ГОСТ 23360-78 исп. 2 - призматическая с плоскими торцами\n3. ГОСТ 24071-97 - сегментная";
    return "Укажите ГОСТ для стандартного изделия.";
}

static QString resolveGostByChoice(const QString &type, int choice) {
    if (type == "bolt") {
        if (choice == 1) return "ГОСТ 7798-70";
        if (choice == 2) return "ГОСТ 7796-70";
        if (choice == 3) return "ГОСТ 7808-70";
    } else if (type == "nut") {
        if (choice == 1) return "ГОСТ 5915-70";
        if (choice == 2) return "ГОСТ 5916-70";
        if (choice == 3) return "ГОСТ 15521-70";
    } else if (type == "washer") {
        if (choice == 1) return "ГОСТ 11371-78";
        if (choice == 2) return "ГОСТ 6958-78";
        if (choice == 3) return "ГОСТ 10450-78";
    } else if (type == "screw") {
        if (choice == 1) return "ГОСТ 11738-84";
        if (choice == 2) return "ГОСТ 1491-80";
        if (choice == 3) return "ГОСТ 17475-80";
    } else if (type == "bearing") {
        if (choice == 1) return "ГОСТ 8338-75";
        if (choice == 2) return "ГОСТ 7242-81";
        if (choice == 3) return "ГОСТ 8328-75";
    } else if (type == "pin") {
        if (choice == 1) return "ГОСТ 3128-70";
        if (choice == 2) return "ГОСТ 24296-93";
        if (choice == 3) return "ГОСТ 3129-70";
    } else if (type == "key") {
        if (choice == 1) return "ГОСТ 23360-78";
        if (choice == 2) return "ГОСТ 23360-78 исп. 2";
        if (choice == 3) return "ГОСТ 24071-97";
    }
    return QString();
}

static bool hasValidParam(const QJsonObject &params, const QString &key) {
    if (!params.contains(key)) return false;
    QJsonValue v = params.value(key);
    if (v.isNull() || v.isUndefined()) return false;
    if (v.isString()) return !v.toString().trimmed().isEmpty();
    if (v.isDouble()) return v.toDouble() > 0.0;
    return true;
}

OllamaClient::OllamaClient(QObject *parent)
    : QObject(parent),
      m_nam(new QNetworkAccessManager(this)),
      m_baseUrl("http://127.0.0.1:11434"),
      m_modelName("qwen2.5-coder:14b"),
      m_isOnline(false),
      m_isBusy(false),
      m_modelWarmedUp(false)
{
    m_pingTimer = new QTimer(this);
    connect(m_pingTimer, &QTimer::timeout, this, &OllamaClient::checkConnection);
    m_pingTimer->start(8000);
    checkConnection();
}

void OllamaClient::setModelName(const QString &model) {
    if (m_modelName != model) {
        m_modelName = model;
        m_modelWarmedUp = false;
        if (m_isOnline) {
            warmupModel();
        }
    }
}

QString OllamaClient::modelName() const {
    return m_modelName;
}

void OllamaClient::clearHistory() {
    m_history = QJsonArray();
}

void OllamaClient::updateContext(const QJsonArray &features, const QJsonObject &selection, const QJsonArray &tree) {
    Q_UNUSED(tree);
    QJsonArray compactFeatures;
    for (const QJsonValue &v : features) {
        if (!v.isObject()) continue;
        QJsonObject f = v.toObject();
        QJsonObject item;
        item["id"] = f.value("id");
        item["type"] = f.value("type");
        item["bounds"] = f.value("bounds");
        compactFeatures.append(item);
    }
    QJsonObject compactSel;
    compactSel["selected_faces"] = selection.value("selected_faces").toInt();
    compactSel["selected_edges"] = selection.value("selected_edges").toInt();

    QJsonObject ctx;
    ctx["features"] = compactFeatures;
    ctx["selection"] = compactSel;
    m_currentContext = ctx;
}

void OllamaClient::checkConnection() {
    if (m_isBusy) return;
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
    if (m_isOnline && !m_modelWarmedUp) {
        m_modelWarmedUp = true;
        warmupModel();
    }
    reply->deleteLater();
}

void OllamaClient::warmupModel() {
    QNetworkRequest req(QUrl(m_baseUrl + "/api/chat"));
    req.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");
    QJsonArray messages;
    QJsonObject sysMsg;
    sysMsg["role"] = "system";
    sysMsg["content"] = buildSystemPrompt();
    messages.append(sysMsg);

    QJsonObject payload;
    payload["model"] = m_modelName;
    payload["messages"] = messages;
    payload["stream"] = false;
    payload["keep_alive"] = -1;
    QJsonObject options;
    options["num_ctx"] = 2048;
    options["num_predict"] = 1;
    payload["options"] = options;

    QNetworkReply *reply = m_nam->post(req, QJsonDocument(payload).toJson(QJsonDocument::Compact));
    connect(reply, &QNetworkReply::finished, reply, &QObject::deleteLater);
}

QString OllamaClient::buildSystemPrompt() const {
    return QString(
        "Ты - модуль автоматизации проектирования АЗИМУТ в САПР КОМПАС-3D. Отвечай СТРОГО валидным JSON на русском языке (поле reply сухое, до 5 слов, используй только обычный дефис - без тире и кавычек-елочек):\n"
        "{\"reply\":\"Команда принята в обработку\",\"commands\":[{\"action\":\"build|update|delete|clear|undo|doc_new|doc_save|doc_delete|ask\","
        "\"type\":\"plate|cylinder|tube|polygon|cone|sphere|torus|dome|hole|holes_corner|holes_circ|holes_grid|cut_box|slot|cross_slot|t_slot|counterbore|countersink|groove|chamfer|fillet|shell|shaft|rect_tube|l_profile|u_profile|i_beam|t_beam|spring|gear|flange|rib|bolt|nut|washer|screw|bearing|pin|key|appearance|profile\","
        "\"id\":\"id_1\",\"params\":{}}]}\n"
        "КООРДИНАТЫ:\n"
        "1. Плоскость XOZ (y_offset=0). Первая деталь в (x:0, z:0, y_offset:0).\n"
        "2. Вверх: +Y (direction:1), Вниз: -Y (direction:-1). Вправо: -Z, Влево: +Z, Вперед: -X, Назад: +X.\n"
        "3. На верхней грани: base:\"top\", direction:1; на нижней: base:\"bottom\", direction:-1.\n"
        "4. holes_corner: width, length, d, offset. Уклон angle: >0 наружу, <0 внутрь.\n"
        "5. Стандартные изделия (bolt, nut, washer, screw, bearing, pin, key): М24 задает d:24, М24х180 задает d:24 и length:180. Если нет gost или размеров - action:\"ask\"."
    );
}

bool OllamaClient::tryHandleFastPath(const QString &userPrompt) {
    QString dialogText;
    for (const QJsonValue &hVal : m_history) {
        if (hVal.isObject() && hVal.toObject().value("role").toString() == "user") {
            dialogText += " " + hVal.toObject().value("content").toString();
        }
    }
    dialogText += " " + userPrompt;
    QString lowerDialog = dialogText.toLower();

    const QStringList nonStdKeywords = {
        "плит", "пластин", "куб", "короб", "цилиндр", "труб", "призм", "конус",
        "шар", "сфер", "тор", "купол", "отверст", "карман", "вырез", "паз",
        "цеков", "зенков", "канавк", "фаск", "скругл", "оболочк", "вал",
        "уголок", "швеллер", "двутавр", "тавр", "пружин", "шестерн", "зубчат",
        "фланец", "ребр", "цвет", "материал", "покрас"
    };
    for (const QString &kw : nonStdKeywords) {
        if (lowerDialog.contains(kw)) {
            return false;
        }
    }

    QString detectedStdType;
    if (lowerDialog.contains("болт")) detectedStdType = "bolt";
    else if (lowerDialog.contains("гайк")) detectedStdType = "nut";
    else if (lowerDialog.contains("шайб")) detectedStdType = "washer";
    else if (lowerDialog.contains("винт")) detectedStdType = "screw";
    else if (lowerDialog.contains("подшипник")) detectedStdType = "bearing";
    else if (lowerDialog.contains("штифт")) detectedStdType = "pin";
    else if (lowerDialog.contains("шпонк")) detectedStdType = "key";

    if (detectedStdType.isEmpty()) {
        return false;
    }

    QJsonObject params;
    QRegularExpression gostRx("(\\d{4,5}-\\d{2})");
    QRegularExpressionMatch gostMatch = gostRx.match(dialogText);
    if (gostMatch.hasMatch()) {
        params["gost"] = "ГОСТ " + gostMatch.captured(1);
    } else {
        QRegularExpression choiceRx("^\\s*([123])\\s*$");
        QRegularExpressionMatch choiceMatch = choiceRx.match(userPrompt);
        if (choiceMatch.hasMatch()) {
            QString resolved = resolveGostByChoice(detectedStdType, choiceMatch.captured(1).toInt());
            if (!resolved.isEmpty()) {
                params["gost"] = resolved;
            }
        }
    }

    QRegularExpression metricRx("(?:^|\\s)[МмMm]\\s*(\\d+(?:[.,]\\d+)?)(?:\\s*[xхXХ*]\\s*(\\d+(?:[.,]\\d+)?))?");
    QRegularExpressionMatchIterator metricIt = metricRx.globalMatch(dialogText);
    while (metricIt.hasNext()) {
        QRegularExpressionMatch m = metricIt.next();
        params["d"] = m.captured(1).replace(',', '.').toDouble();
        if (!m.captured(2).isEmpty()) {
            params["length"] = m.captured(2).replace(',', '.').toDouble();
        }
    }

    QRegularExpression diamRx("(?:диаметр\\w*|\\bd\\b)\\s*[:=]?\\s*(\\d+(?:[.,]\\d+)?)");
    QRegularExpressionMatch diamMatch = diamRx.match(lowerDialog);
    if (diamMatch.hasMatch() && !hasValidParam(params, "d")) {
        params["d"] = diamMatch.captured(1).replace(',', '.').toDouble();
    }

    QRegularExpression lenRx("(?:длин\\w*|length|высот\\w*)\\s*[:=]?\\s*(\\d+(?:[.,]\\d+)?)");
    QRegularExpressionMatch lenMatch = lenRx.match(lowerDialog);
    if (lenMatch.hasMatch() && !hasValidParam(params, "length")) {
        params["length"] = lenMatch.captured(1).replace(',', '.').toDouble();
    }

    QRegularExpression singleNumRx("^\\s*(\\d+(?:[.,]\\d+)?)\\s*(?:мм|mm)?\\s*$");
    QRegularExpressionMatch singleNumMatch = singleNumRx.match(userPrompt);
    if (singleNumMatch.hasMatch()) {
        double val = singleNumMatch.captured(1).replace(',', '.').toDouble();
        if (val > 3.0) {
            if (!hasValidParam(params, "d")) {
                params["d"] = val;
            } else if (!hasValidParam(params, "length")) {
                params["length"] = val;
            }
        }
    }

    QString gost = params.value("gost").toString().trimmed();
    if (gost.isEmpty()) {
        QString replyText = sanitizeText(gostPromptForType(detectedStdType));
        QJsonObject uMsg;
        uMsg["role"] = "user";
        uMsg["content"] = userPrompt;
        m_history.append(uMsg);
        QJsonObject aMsg;
        aMsg["role"] = "assistant";
        aMsg["content"] = replyText;
        m_history.append(aMsg);
        QTimer::singleShot(0, this, [this, replyText]() {
            emit clarificationNeeded(replyText);
        });
        return true;
    }

    QStringList missing;
    if (detectedStdType == "bolt" || detectedStdType == "screw" || detectedStdType == "pin") {
        if (!hasValidParam(params, "d")) missing << "диаметр (d)";
        if (!hasValidParam(params, "length")) missing << "длину (length)";
    } else if (detectedStdType == "nut" || detectedStdType == "washer") {
        if (!hasValidParam(params, "d")) missing << "диаметр (d)";
    } else if (detectedStdType == "bearing") {
        if (!hasValidParam(params, "d")) missing << "внутренний диаметр (d)";
        if (!hasValidParam(params, "D")) missing << "наружный диаметр (D)";
        if (!hasValidParam(params, "B")) missing << "ширину (B)";
    } else if (detectedStdType == "key") {
        if (!hasValidParam(params, "b")) missing << "ширину (b)";
        if (!hasValidParam(params, "h")) missing << "высоту (h)";
        if (!hasValidParam(params, "length")) missing << "длину (length)";
    }

    if (!missing.isEmpty()) {
        QString replyText = sanitizeText(QString("Выбран %1. Укажите недостающие параметры: %2.").arg(gost, missing.join(", ")));
        QJsonObject uMsg;
        uMsg["role"] = "user";
        uMsg["content"] = userPrompt;
        m_history.append(uMsg);
        QJsonObject aMsg;
        aMsg["role"] = "assistant";
        aMsg["content"] = replyText;
        m_history.append(aMsg);
        QTimer::singleShot(0, this, [this, replyText]() {
            emit clarificationNeeded(replyText);
        });
        return true;
    }

    m_history = QJsonArray();
    QJsonObject cmd;
    cmd["action"] = "build";
    cmd["type"] = detectedStdType;
    cmd["id"] = detectedStdType + "_1";
    cmd["params"] = params;
    QJsonArray cmds;
    cmds.append(cmd);
    QJsonObject outPayload;
    outPayload["commands"] = cmds;
    QString finalReply = sanitizeText(QString("Импорт изделия по %1.").arg(gost));
    QTimer::singleShot(0, this, [this, finalReply, outPayload]() {
        emit commandsReady(finalReply, outPayload);
    });
    return true;
}

void OllamaClient::sendPrompt(const QString &userPrompt) {
    m_lastUserPrompt = userPrompt;
    if (tryHandleFastPath(userPrompt)) {
        return;
    }

    m_isBusy = true;
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
    userMsg["content"] = QString("КОНТЕКСТ:%1\nЗАПРОС:%2").arg(kompasContext, userPrompt);
    messages.append(userMsg);

    QJsonObject payload;
    payload["model"] = m_modelName;
    payload["messages"] = messages;
    payload["stream"] = false;
    payload["format"] = "json";
    payload["keep_alive"] = -1;

    QJsonObject options;
    options["temperature"] = 0.0;
    options["top_k"] = 1;
    options["num_ctx"] = 2048;
    options["num_predict"] = 220;
    options["num_batch"] = 512;
    payload["options"] = options;

    QNetworkReply *reply = m_nam->post(req, QJsonDocument(payload).toJson(QJsonDocument::Compact));
    connect(reply, &QNetworkReply::finished, this, &OllamaClient::onReplyFinished);
}

void OllamaClient::onReplyFinished() {
    m_isBusy = false;
    QNetworkReply *reply = qobject_cast<QNetworkReply*>(sender());
    if (!reply) return;

    if (reply->error() != QNetworkReply::NoError) {
        emit errorOccurred(sanitizeText("Ошибка связи с локальным сервером: " + reply->errorString()));
        reply->deleteLater();
        return;
    }

    QByteArray rawData = reply->readAll();
    reply->deleteLater();

    QJsonDocument outerDoc = QJsonDocument::fromJson(rawData);
    if (!outerDoc.isObject()) {
        emit errorOccurred("Некорректный формат ответа от локального сервера.");
        return;
    }

    QString content = sanitizeText(outerDoc.object().value("message").toObject().value("content").toString().trimmed());
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
    QString replyText = sanitizeText(obj.value("reply").toString("Готово."));
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
                if (!hasValidParam(params, "d") && !hasValidParam(params, "diameter")) {
                    params["d"] = metricMatch.captured(1).replace(',', '.').toDouble();
                }
                if (!metricMatch.captured(2).isEmpty() && !hasValidParam(params, "length") && !hasValidParam(params, "height")) {
                    params["length"] = metricMatch.captured(2).replace(',', '.').toDouble();
                }
            }
            if (!hasValidParam(params, "gost") && gostMatch.hasMatch()) {
                params["gost"] = "ГОСТ " + gostMatch.captured(1);
            }
            cmd["params"] = params;

            QString gost = params.value("gost").toString().trimmed();
            if (gost.isEmpty()) {
                needsAsk = true;
                replyText = sanitizeText(gostPromptForType(type));
                continue;
            }

            QStringList missing;
            if (type == "bolt" || type == "screw" || type == "pin") {
                if (!hasValidParam(params, "d") && !hasValidParam(params, "diameter")) missing << "диаметр (d)";
                if (!hasValidParam(params, "length") && !hasValidParam(params, "height")) missing << "длину (length)";
            } else if (type == "nut" || type == "washer") {
                if (!hasValidParam(params, "d") && !hasValidParam(params, "diameter")) missing << "диаметр (d)";
            } else if (type == "bearing") {
                if (!hasValidParam(params, "d")) missing << "внутренний диаметр (d)";
                if (!hasValidParam(params, "D")) missing << "наружный диаметр (D)";
                if (!hasValidParam(params, "B") && !hasValidParam(params, "width") && !hasValidParam(params, "length")) missing << "ширину (B)";
            } else if (type == "key") {
                if (!hasValidParam(params, "b") && !hasValidParam(params, "width")) missing << "ширину (b)";
                if (!hasValidParam(params, "h") && !hasValidParam(params, "height")) missing << "высоту (h)";
                if (!hasValidParam(params, "length")) missing << "длину (length)";
            }

            if (!missing.isEmpty()) {
                needsAsk = true;
                replyText = sanitizeText(QString("Выбран %1. Укажите недостающие параметры: %2.").arg(gost, missing.join(", ")));
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

    replyText = sanitizeText(replyText);

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