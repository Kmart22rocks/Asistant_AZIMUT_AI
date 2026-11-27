#include "OllamaClient.h"
#include <QJsonDocument>
#include <QNetworkRequest>
#include <QUrl>
#include <QRegularExpression>
#include <cmath>

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

static QList<double> extractUserNumbers(const QString &text) {
    QList<double> nums;
    QRegularExpression rx("(?<!\\d)\\d+(?:[.,]\\d+)?(?!\\d)");
    QRegularExpressionMatchIterator it = rx.globalMatch(text);
    while (it.hasNext()) {
        QRegularExpressionMatch m = it.next();
        double v = m.captured(0).replace(',', '.').toDouble();
        nums.append(v);
    }
    return nums;
}

static bool isNumberInUserList(double val, const QList<double> &userNums) {
    for (double u : userNums) {
        if (std::abs(val - u) < 1e-2) return true;
        if (std::abs(val - u * 2.0) < 1e-2) return true;
        if (std::abs(val * 2.0 - u) < 1e-2) return true;
    }
    return false;
}

static bool isMoveCommandPrompt(const QString &lowerText) {
    return lowerText.contains("опуст") ||
           lowerText.contains("подним") ||
           lowerText.contains("перемест") ||
           lowerText.contains("сдвин") ||
           lowerText.contains("подвин") ||
           lowerText.contains("перенес") ||
           lowerText.contains("вниз") ||
           lowerText.contains("вверх") ||
           lowerText.contains("вправ") ||
           lowerText.contains("влев") ||
           lowerText.contains("вперед") ||
           lowerText.contains("вперёд") ||
           lowerText.contains("назад");
}

static bool validateAndCleanBuildParams(
    QString &type,
    QJsonObject &params,
    const QString &dialogText,
    const QString &lastPrompt,
    QString &missingReply)
{
    QString lowerDialog = dialogText.toLower();
    QString lowerLast = lastPrompt.toLower();
    QList<double> userNums = extractUserNumbers(dialogText);
    QList<double> lastNums = extractUserNumbers(lastPrompt);

    if (lowerLast.contains("фаск")) {
        type = "chamfer";
        params.remove("width");
        params.remove("length");
        params.remove("height");
        if (!lastNums.isEmpty()) {
            params["size"] = lastNums.first();
        }
    } else if (lowerLast.contains("скругл")) {
        type = "fillet";
        params.remove("width");
        params.remove("length");
        params.remove("height");
        if (!lastNums.isEmpty()) {
            params["radius"] = lastNums.first();
        }
    } else if (lowerLast.contains("оболочк")) {
        type = "shell";
        if (!lastNums.isEmpty()) {
            params["thickness"] = lastNums.first();
        }
    } else if (lowerDialog.contains("куб") && (type == "plate" || type == "box" || type == "cube")) {
        type = "cube";
    }

    if (type == "appearance" || type == "color" || type == "material") {
        return true;
    }

    const QStringList dimKeys = {
        "size", "width", "length", "height", "diameter", "d", "d1", "d2",
        "radius", "r", "depth", "thickness", "wall", "t", "step", "step_x", "step_z",
        "offset", "inner_diameter", "bore", "outer_d", "inner_d", "circle_d", "pcd",
        "module", "m", "teeth", "wire_d", "pitch"
    };

    for (const QString &k : dimKeys) {
        if (type == "holes_corner" && (k == "width" || k == "length" || k == "offset")) {
            continue;
        }
        if (params.contains(k) && params.value(k).isDouble()) {
            double v = params.value(k).toDouble();
            if (!isNumberInUserList(v, userNums)) {
                params.remove(k);
            }
        }
    }

    if (type == "cube") {
        if (userNums.isEmpty()) {
            missingReply = "Укажите длину стороны куба (в мм).";
            return false;
        }
        double side = userNums.last();
        params["size"] = side;
        params["width"] = side;
        params["length"] = side;
        params["height"] = side;
        return true;
    }

    if (type == "plate" || type == "box") {
        bool isSquare = lowerDialog.contains("квадрат");
        int minNums = isSquare ? 2 : 3;
        QStringList miss;
        if (!hasValidParam(params, "length")) miss << "длину (length)";
        if (!hasValidParam(params, "width") && !isSquare) miss << "ширину (width)";
        if (!hasValidParam(params, "height") && !hasValidParam(params, "thickness")) miss << "высоту/толщину (height)";
        if (userNums.size() < minNums || !miss.isEmpty()) {
            if (miss.isEmpty()) {
                miss << "длину" << "ширину" << "высоту/толщину";
            }
            missingReply = QString("Укажите недостающие параметры для построения плиты: %1 (в мм).").arg(miss.join(", "));
            return false;
        }
        if (isSquare && !hasValidParam(params, "width")) {
            params["width"] = params.value("length");
        }
        return true;
    }

    if (type == "cylinder" || type == "boss_cyl") {
        QStringList miss;
        if (!hasValidParam(params, "diameter") && !hasValidParam(params, "d") && !hasValidParam(params, "radius") && !hasValidParam(params, "r"))
            miss << "диаметр (d)";
        if (!hasValidParam(params, "height") && !hasValidParam(params, "h") && !hasValidParam(params, "length"))
            miss << "высоту (height)";
        if (userNums.size() < 2 || !miss.isEmpty()) {
            if (miss.isEmpty()) miss << "диаметр (d)" << "высоту (height)";
            missingReply = QString("Укажите недостающие параметры для построения цилиндра: %1 (в мм).").arg(miss.join(", "));
            return false;
        }
        return true;
    }

    if (type == "tube") {
        QStringList miss;
        if (!hasValidParam(params, "diameter") && !hasValidParam(params, "d") && !hasValidParam(params, "outer_d"))
            miss << "наружный диаметр (d)";
        if (!hasValidParam(params, "inner_diameter") && !hasValidParam(params, "inner_d") && !hasValidParam(params, "wall") && !hasValidParam(params, "thickness"))
            miss << "внутренний диаметр (inner_diameter) или толщину стенки (wall)";
        if (!hasValidParam(params, "height") && !hasValidParam(params, "h") && !hasValidParam(params, "length"))
            miss << "высоту (height)";
        if (userNums.size() < 3 || !miss.isEmpty()) {
            if (miss.isEmpty()) miss << "наружный диаметр" << "внутренний диаметр" << "высоту";
            missingReply = QString("Укажите недостающие параметры для построения трубы: %1 (в мм).").arg(miss.join(", "));
            return false;
        }
        return true;
    }

    if (type == "sphere" || type == "ball") {
        if (userNums.isEmpty() || (!hasValidParam(params, "diameter") && !hasValidParam(params, "d") && !hasValidParam(params, "radius") && !hasValidParam(params, "r"))) {
            missingReply = "Укажите диаметр сферы (d) в мм.";
            return false;
        }
        return true;
    }

    if (type == "cone") {
        QStringList miss;
        if (!hasValidParam(params, "d1") && !hasValidParam(params, "diameter") && !hasValidParam(params, "d"))
            miss << "диаметр основания (d1)";
        if (!hasValidParam(params, "height") && !hasValidParam(params, "h"))
            miss << "высоту (height)";
        if (userNums.size() < 2 || !miss.isEmpty()) {
            if (miss.isEmpty()) miss << "диаметр основания (d1)" << "высоту (height)";
            missingReply = QString("Укажите недостающие параметры для построения конуса: %1 (в мм).").arg(miss.join(", "));
            return false;
        }
        return true;
    }

    if (type == "polygon" || type == "prism") {
        QStringList miss;
        if (!hasValidParam(params, "diameter") && !hasValidParam(params, "d") && !hasValidParam(params, "size"))
            miss << "диаметр вписанной/описанной окружности (d)";
        if (!hasValidParam(params, "height") && !hasValidParam(params, "h"))
            miss << "высоту (height)";
        if (userNums.size() < 2 || !miss.isEmpty()) {
            if (miss.isEmpty()) miss << "диаметр (d)" << "высоту (height)";
            missingReply = QString("Укажите недостающие параметры для построения призмы: %1 (в мм).").arg(miss.join(", "));
            return false;
        }
        return true;
    }

    if (type == "chamfer") {
        if (userNums.isEmpty() || (!hasValidParam(params, "size") && !hasValidParam(params, "s") && !hasValidParam(params, "distance"))) {
            missingReply = "Укажите размер фаски (size) в мм.";
            return false;
        }
        return true;
    }

    if (type == "fillet") {
        if (userNums.isEmpty() || (!hasValidParam(params, "radius") && !hasValidParam(params, "r") && !hasValidParam(params, "size"))) {
            missingReply = "Укажите радиус скругления (radius) в мм.";
            return false;
        }
        return true;
    }

    if (type == "shell") {
        if (userNums.isEmpty() || (!hasValidParam(params, "thickness") && !hasValidParam(params, "wall") && !hasValidParam(params, "t"))) {
            missingReply = "Укажите толщину стенки оболочки (thickness) в мм.";
            return false;
        }
        return true;
    }

    if (type == "hole" || type == "cut_cyl") {
        QStringList miss;
        if (!hasValidParam(params, "diameter") && !hasValidParam(params, "d"))
            miss << "диаметр отверстия (d)";
        if (lowerDialog.contains("глух") && !hasValidParam(params, "depth"))
            miss << "глубину отверстия (depth)";
        if (userNums.isEmpty() || !miss.isEmpty()) {
            if (miss.isEmpty()) miss << "диаметр отверстия (d)";
            missingReply = QString("Укажите недостающие параметры для отверстия: %1 (в мм).").arg(miss.join(", "));
            return false;
        }
        return true;
    }

    if (type == "holes_corner") {
        if (userNums.isEmpty() || (!hasValidParam(params, "diameter") && !hasValidParam(params, "d"))) {
            missingReply = "Укажите диаметр угловых отверстий (d) и при необходимости отступ от края (offset) в мм.";
            return false;
        }
        return true;
    }

    if (type == "holes_circ") {
        QStringList miss;
        if (!hasValidParam(params, "diameter") && !hasValidParam(params, "d"))
            miss << "диаметр отверстий (d)";
        if (!hasValidParam(params, "circle_d") && !hasValidParam(params, "pcd") && !hasValidParam(params, "radius"))
            miss << "диаметр делительной окружности (circle_d)";
        if (userNums.size() < 2 || !miss.isEmpty()) {
            if (miss.isEmpty()) miss << "диаметр отверстий (d)" << "диаметр окружности центров (circle_d)";
            missingReply = QString("Укажите недостающие параметры для кругового массива отверстий: %1.").arg(miss.join(", "));
            return false;
        }
        return true;
    }

    if (type == "holes_grid") {
        if (userNums.size() < 2 || (!hasValidParam(params, "diameter") && !hasValidParam(params, "d"))) {
            missingReply = "Укажите параметры сетки отверстий: диаметр (d), шаг (step) и количество (count_x, count_z).";
            return false;
        }
        return true;
    }

    if (type == "cut_box" || type == "pocket") {
        QStringList miss;
        if (!hasValidParam(params, "length")) miss << "длину (length)";
        if (!hasValidParam(params, "width")) miss << "ширину (width)";
        if (!hasValidParam(params, "depth") && !hasValidParam(params, "height")) miss << "глубину (depth)";
        if (userNums.size() < 2 || !miss.isEmpty()) {
            if (miss.isEmpty()) miss << "длину" << "ширину" << "глубину";
            missingReply = QString("Укажите недостающие параметры выреза/кармана: %1 (в мм).").arg(miss.join(", "));
            return false;
        }
        return true;
    }

    if (type == "slot") {
        QStringList miss;
        if (!hasValidParam(params, "length")) miss << "длину паза (length)";
        if (!hasValidParam(params, "width") && !hasValidParam(params, "d")) miss << "ширину паза (width)";
        if (userNums.size() < 2 || !miss.isEmpty()) {
            if (miss.isEmpty()) miss << "длину паза (length)" << "ширину паза (width)";
            missingReply = QString("Укажите недостающие параметры паза: %1 (в мм).").arg(miss.join(", "));
            return false;
        }
        return true;
    }

    if (userNums.isEmpty()) {
        missingReply = "Укажите габаритные размеры элемента (в мм).";
        return false;
    }

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
        QJsonObject p = f.value("params").toObject();
        p.remove("edge_coords");
        item["params"] = p;
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
        "Ты - модуль автоматизации проектирования АЗИМУТ в САПР КОМПАС-3D. Отвечай СТРОГО валидным JSON на русском языке (используй только обычный дефис - без тире и кавычек-елочек):\n"
        "{\"reply\":\"Команда принята в обработку\",\"commands\":[{\"action\":\"build|update|delete|clear|undo|doc_new|doc_save|doc_delete|ask\","
        "\"type\":\"cube|plate|cylinder|tube|polygon|cone|sphere|torus|dome|hole|holes_corner|holes_circ|holes_grid|cut_box|slot|cross_slot|t_slot|counterbore|countersink|groove|chamfer|fillet|shell|shaft|rect_tube|l_profile|u_profile|i_beam|t_beam|spring|gear|flange|rib|bolt|nut|washer|screw|bearing|pin|key|appearance|profile\","
        "\"id\":\"уникальный_id\",\"params\":{}}]}\n"
        "ПРАВИЛА:\n"
        "1. ЗАПРЕЩЕНО придумывать размеры по умолчанию (100, 50 и т.д.), если пользователь их не указал! Если для новой операции (build) не указаны размеры (для cube: size; для plate: length, width, height; для cylinder: d, height; для chamfer: size; для fillet: radius; для hole: d) - верни action:\"ask\" и спроси недостающие размеры в reply.\n"
        "2. Фаска (type:\"chamfer\", params:{\"size\":...}) и скругление (type:\"fillet\", params:{\"radius\":...}) - отдельные операции, никогда не меняй ими размер куба или плиты.\n"
        "3. Плоскость XOZ (y_offset=0). Первая деталь в (x:0, z:0, y_offset:0). Вверх: +Y (direction:1), Вниз: -Y (direction:-1). Вправо: -Z, Влево: +Z, Вперед: -X, Назад: +X.\n"
        "4. На верхней грани: base:\"top\", direction:1; на нижней: base:\"bottom\", direction:-1.\n"
        "5. При перемещении детали передавай ТОЛЬКО одну команду action:\"update\" для первой базовой детали с новыми координатами (x, z, y_offset), НЕ меняя ее размеры.\n"
        "6. При сохранении детали используй action:\"doc_save\", params:{\"name\":\"имя_файла\",\"dir\":\"D:\\\\Database AZIMUT\"}.\n"
        "7. Стандартные изделия (bolt, nut, washer, screw, bearing, pin, key): М24 задает d:24, М24х180 задает d:24 и length:180. Если нет gost или размеров - action:\"ask\"."
    );
}

bool OllamaClient::tryHandleFastPath(const QString &userPrompt) {
    QString trimmedPrompt = userPrompt.trimmed();
    QString lowerPrompt = trimmedPrompt.toLower();

    if (lowerPrompt.contains("сохран")) {
        QString fileName = "Деталь_АЗИМУТ";
        QRegularExpression nameRx("(?:как|именем|файл|деталь|проект)\\s+[\"«]?([\\wА-Яа-яЁё0-9_\\-]+)[\"»]?", QRegularExpression::CaseInsensitiveOption);
        QRegularExpressionMatch m = nameRx.match(trimmedPrompt);
        if (m.hasMatch()) {
            QString candidate = m.captured(1).trimmed();
            if (!candidate.isEmpty() && candidate.toLower() != "как" && candidate.toLower() != "в") {
                fileName = candidate;
            }
        }
        QJsonObject params;
        params["name"] = fileName;
        params["dir"] = "D:\\Database AZIMUT";
        QJsonObject cmd;
        cmd["action"] = "doc_save";
        cmd["type"] = "doc_save";
        cmd["id"] = "save_1";
        cmd["params"] = params;
        QJsonArray cmds;
        cmds.append(cmd);
        QJsonObject outPayload;
        outPayload["commands"] = cmds;
        QString finalReply = "Сохранение файла в D:\\Database AZIMUT.";
        QTimer::singleShot(0, this, [this, finalReply, outPayload]() {
            emit commandsReady(finalReply, outPayload);
        });
        return true;
    }

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
        "фланец", "ребр", "цвет", "материал", "покрас", "перемест", "сдвин"
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
    QString lowerDialog = dialogText.toLower();
    QString lowerLast = m_lastUserPrompt.toLower();

    QRegularExpression metricRx("(?:^|\\s)[МмMm]\\s*(\\d+(?:[.,]\\d+)?)(?:\\s*[xхXХ*]\\s*(\\d+(?:[.,]\\d+)?))?");
    QRegularExpressionMatch metricMatch = metricRx.match(dialogText);
    QRegularExpression gostRx("(\\d{4,5}-\\d{2})");
    QRegularExpressionMatch gostMatch = gostRx.match(dialogText);

    QString detectedStdType;
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

    bool hasExistingFeatures = !m_currentContext.value("features").toArray().isEmpty();
    bool isMovePrompt = isMoveCommandPrompt(lowerLast);
    bool isModificationPrompt = m_history.isEmpty() && hasExistingFeatures && (
        isMovePrompt || lowerLast.contains("пусть") || lowerLast.contains("измен") ||
        lowerLast.contains("поменя") || lowerLast.contains("увелич") || lowerLast.contains("уменьш")
    );

    QJsonArray executableCommands;
    bool needsAsk = false;
    bool moveCommandAdded = false;
    const QStringList stdTypes = {"bolt", "nut", "washer", "screw", "bearing", "pin", "key", "standard_part"};

    for (const QJsonValue &val : commands) {
        if (!val.isObject()) continue;
        QJsonObject cmd = val.toObject();
        QString action = cmd.value("action").toString("build").toLower();
        QString type = cmd.value("type").toString().toLower();

        if (type == "standard_part" && !detectedStdType.isEmpty()) {
            type = detectedStdType;
            cmd["type"] = type;
        }

        QJsonObject params = cmd.value("params").toObject();

        if (action == "doc_save" || type == "doc_save" || action == "save") {
            params["dir"] = "D:\\Database AZIMUT";
            cmd["action"] = "doc_save";
            cmd["params"] = params;
            executableCommands.append(cmd);
            continue;
        }

        if (lowerLast.contains("фаск") && !isMovePrompt && action != "delete" && action != "undo" && action != "clear") {
            type = "chamfer";
            cmd["type"] = "chamfer";
            cmd["id"] = "chamfer_1";
            QList<double> lNums = extractUserNumbers(m_lastUserPrompt);
            params.remove("width");
            params.remove("length");
            params.remove("height");
            if (!lNums.isEmpty()) {
                params["size"] = lNums.first();
                if (action == "ask" || action == "none") action = "build";
            } else {
                action = "ask";
            }
            cmd["action"] = action;
            cmd["params"] = params;
        } else if (lowerLast.contains("скругл") && !isMovePrompt && action != "delete" && action != "undo" && action != "clear") {
            type = "fillet";
            cmd["type"] = "fillet";
            cmd["id"] = "fillet_1";
            QList<double> lNums = extractUserNumbers(m_lastUserPrompt);
            params.remove("width");
            params.remove("length");
            params.remove("height");
            if (!lNums.isEmpty()) {
                params["radius"] = lNums.first();
                if (action == "ask" || action == "none") action = "build";
            } else {
                action = "ask";
            }
            cmd["action"] = action;
            cmd["params"] = params;
        }

        if (stdTypes.contains(type) && !isModificationPrompt) {
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

        if (isModificationPrompt && action == "build" && type != "chamfer" && type != "fillet") {
            action = "update";
            cmd["action"] = "update";
        }

        if (action == "ask" || action == "none") {
            QString missingMsg;
            if (!validateAndCleanBuildParams(type, params, dialogText, m_lastUserPrompt, missingMsg)) {
                replyText = sanitizeText(missingMsg);
                needsAsk = true;
                continue;
            }
            action = "build";
            cmd["action"] = "build";
            cmd["type"] = type;
            cmd["params"] = params;
        }

        if (action == "build") {
            QString missingMsg;
            if (!validateAndCleanBuildParams(type, params, dialogText, m_lastUserPrompt, missingMsg)) {
                needsAsk = true;
                replyText = sanitizeText(missingMsg);
                continue;
            }
            cmd["type"] = type;
            cmd["params"] = params;
        } else if (action == "update") {
            bool hasPositionChange = isMovePrompt ||
                                     params.contains("x") ||
                                     params.contains("z") ||
                                     params.contains("y_offset") ||
                                     params.contains("z_offset");
            if (hasPositionChange) {
                if (moveCommandAdded) {
                    continue;
                }
                params.remove("size");
                params.remove("width");
                params.remove("length");
                params.remove("height");
                params.remove("diameter");
                params.remove("d");
                params.remove("radius");
                params.remove("r");
                moveCommandAdded = true;
            } else if (lowerLast.contains("куб") || type == "cube") {
                QList<double> lNums = extractUserNumbers(m_lastUserPrompt);
                if (lNums.size() == 1) {
                    double side = lNums.first();
                    params["size"] = side;
                    params["width"] = side;
                    params["length"] = side;
                    params["height"] = side;
                }
            }
            cmd["params"] = params;
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