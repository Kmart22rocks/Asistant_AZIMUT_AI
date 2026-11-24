#include "OllamaClient.h"
#include <QNetworkRequest>
#include <QNetworkReply>
#include <QJsonDocument>
#include <QUrl>

OllamaClient::OllamaClient(QObject* parent)
    : QObject(parent),
      m_net(new QNetworkAccessManager(this)),
      m_modelName("qwen2.5-coder:14b") {
}

void OllamaClient::unloadModelFromMemory(const QString& modelName) {
    if (modelName.isEmpty()) return;
    QJsonObject reqBody;
    reqBody["model"] = modelName;
    reqBody["keep_alive"] = 0;

    QNetworkRequest req(QUrl("http://127.0.0.1:11434/api/generate"));
    req.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");
    QNetworkReply* reply = m_net->post(req, QJsonDocument(reqBody).toJson(QJsonDocument::Compact));
    connect(reply, &QNetworkReply::finished, reply, &QObject::deleteLater);
}

void OllamaClient::setModelName(const QString& modelName) {
    if (m_modelName == modelName) return;
    QString oldModel = m_modelName;
    m_modelName = modelName;
    unloadModelFromMemory(oldModel);
}

QString OllamaClient::modelName() const {
    return m_modelName;
}

void OllamaClient::updateContext(const QJsonArray& features, const QJsonObject& selection, const QJsonArray& nativeTree) {
    m_currentFeatures = features;
    m_currentSelection = selection;
    m_nativeTree = nativeTree;
}

QString OllamaClient::buildSystemPrompt() const {
    QString ctxFeatures = QString::fromUtf8(QJsonDocument(m_currentFeatures).toJson(QJsonDocument::Compact));
    QString ctxSel = QString::fromUtf8(QJsonDocument(m_currentSelection).toJson(QJsonDocument::Compact));
    QString ctxTree = QString::fromUtf8(QJsonDocument(m_nativeTree).toJson(QJsonDocument::Compact));

    return QString(
        "Ты — ИИ-конструктор АЗИМУТ для КОМПАС-3D. Отвечай СТРОГО валидным JSON без markdown.\n"
        "Текущие элементы ИИ: %1\n"
        "Выделено мышкой в КОМПАС-3D: %2\n"
        "Дерево модели КОМПАС-3D: %3\n\n"
        "СИСТЕМА КООРДИНАТ:\n"
        "- Базовая плоскость (пол) — ZOX.\n"
        "- Вверх — положительное направление вдоль оси +Y (параметры height, thickness, y_offset).\n"
        "- Вправо — минус по оси Z (z < 0), Влево — плюс по оси Z (z > 0).\n"
        "- Вперёд — минус по оси X (x < 0), Назад — плюс по оси X (x > 0).\n\n"
        "ПРАВИЛА:\n"
        "1. Если не хватает обязательных размеров для нового построения, верни:\n"
        "{\"status\":\"clarify\",\"question\":\"Вежливый вопрос на русском языке\"}\n"
        "2. Иначе верни:\n"
        "{\"status\":\"execute\",\"reply\":\"Краткий ответ на русском\",\"commands\":[{\"action\":\"build|update|delete|undo|clear|doc_new|doc_save|doc_delete\",\"id\":\"уникальный_id\",\"type\":\"тип\",\"params\":{...}}]}\n"
        "3. Доступные типы (type) и параметры (params):\n"
        "- plate / box: {\"width\":W, \"length\":L, \"thickness\":T, \"x\":0, \"z\":0}\n"
        "- cube: {\"size\":S, \"x\":0, \"z\":0}\n"
        "- cylinder: {\"diameter\":D, \"height\":H, \"x\":0, \"z\":0}\n"
        "- tube: {\"outer_diameter\":D, \"inner_diameter\":d, \"height\":H, \"x\":0, \"z\":0}\n"
        "- polygon: {\"sides\":N, \"diameter\":D, \"height\":H, \"x\":0, \"z\":0}\n"
        "- cone: {\"diameter\":D, \"top_diameter\":0, \"height\":H, \"x\":0, \"z\":0}\n"
        "- sphere: {\"diameter\":D, \"x\":0, \"z\":0}\n"
        "- shaft: {\"steps\":[{\"diameter\":D1,\"height\":H1},{\"diameter\":D2,\"height\":H2}], \"inner_diameter\":0}\n"
        "- shell: {\"thickness\":T, \"outward\":false}\n"
        "- slot: {\"length\":L, \"width\":W, \"depth\":H, \"x\":0, \"z\":0, \"is_cut\":true, \"through\":false}\n"
        "- profile: {\"points\":[[x1,z1],[x2,z2],...], \"height\":H, \"is_cut\":false}\n"
        "- hole: {\"diameter\":D, \"x\":0, \"z\":0, \"through\":true, \"depth\":10}\n"
        "- holes_corner: {\"diameter\":D, \"offset\":O, \"plate_width\":W, \"plate_length\":L}\n"
        "- holes_circ: {\"count\":N, \"diameter\":d, \"circle_diameter\":D, \"x\":0, \"z\":0}\n"
        "- holes_grid: {\"diameter\":D, \"count_x\":NX, \"count_z\":NZ, \"step_x\":SX, \"step_z\":SZ, \"x\":0, \"z\":0, \"through\":true}\n"
        "- cut_box: {\"width\":W, \"length\":L, \"depth\":H, \"x\":0, \"z\":0, \"through\":false}\n"
        "- chamfer: {\"distance\":C}\n"
        "- fillet: {\"radius\":R}\n"
        "- appearance: {\"color\":\"red|blue|green|yellow|orange|white|black|gray|steel|aluminum|copper|gold|brass\", \"material\":\"сталь|алюминий|медь|латунь|титан|золото|пластик\"}\n"
        "- Управление проектами .m3d:\n"
        "  * Создать новый проект: {\"action\":\"doc_new\", \"type\":\"doc_new\", \"params\":{\"name\":\"ИмяПроекта\"}}\n"
        "  * Сохранить проект: {\"action\":\"doc_save\", \"type\":\"doc_save\", \"params\":{\"name\":\"ИмяФайла\"}}\n"
        "  * Удалить/закрыть проект: {\"action\":\"doc_delete\", \"type\":\"doc_delete\", \"params\":{\"name\":\"ИмяФайла\"}}\n"
        "4. Для изменения существующего элемента используй action=\"update\" и его id. Для добавления нового элемента всегда используй action=\"build\"."
    ).arg(ctxFeatures, ctxSel, ctxTree);
}

void OllamaClient::sendPrompt(const QString& userText) {
    QString finalPrompt = userText;
    if (!m_pendingUserText.isEmpty()) {
        finalPrompt = m_pendingUserText + ". Уточнение пользователя: " + userText;
    }

    QJsonObject reqBody;
    reqBody["model"] = m_modelName;
    reqBody["system"] = buildSystemPrompt();
    reqBody["prompt"] = finalPrompt;
    reqBody["stream"] = false;
    reqBody["format"] = "json";

    QJsonObject opts;
    opts["temperature"] = 0.1;
    opts["num_gpu"] = 99;
    opts["num_ctx"] = 4096;
    reqBody["options"] = opts;

    QNetworkRequest req(QUrl("http://127.0.0.1:11434/api/generate"));
    req.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");

    QNetworkReply* reply = m_net->post(req, QJsonDocument(reqBody).toJson(QJsonDocument::Compact));
    connect(reply, &QNetworkReply::finished, this, [this, reply, userText]() {
        if (reply->error() != QNetworkReply::NoError) {
            emit errorOccurred(reply->errorString());
            reply->deleteLater();
            return;
        }

        QJsonDocument topDoc = QJsonDocument::fromJson(reply->readAll());
        QString rawResponse = topDoc.object().value("response").toString().trimmed();

        int firstBrace = rawResponse.indexOf('{');
        int lastBrace = rawResponse.lastIndexOf('}');
        if (firstBrace != -1 && lastBrace > firstBrace) {
            rawResponse = rawResponse.mid(firstBrace, lastBrace - firstBrace + 1);
        }

        QJsonDocument cmdDoc = QJsonDocument::fromJson(rawResponse.toUtf8());
        if (!cmdDoc.isObject()) {
            emit errorOccurred("Некорректный JSON от языковой модели.");
            reply->deleteLater();
            return;
        }

        QJsonObject obj = cmdDoc.object();
        QString status = obj.value("status").toString("execute");

        if (status == "clarify" || (obj.contains("question") && !obj.contains("commands"))) {
            if (m_pendingUserText.isEmpty()) {
                m_pendingUserText = userText;
            } else {
                m_pendingUserText += " " + userText;
            }
            QString question = obj.value("question").toString("Уточните, пожалуйста, размеры детали.");
            emit clarificationNeeded(question);
        } else {
            m_pendingUserText.clear();
            QString replyText = obj.value("reply").toString("Выполняю команду в КОМПАС-3D.");
            QJsonArray cmds = obj.value("commands").toArray();
            if (cmds.isEmpty() && (obj.contains("action") || obj.contains("type"))) {
                cmds.append(obj);
            }
            QJsonObject payload;
            payload["commands"] = cmds;
            emit commandsReady(replyText, payload);
        }

        reply->deleteLater();
    });
}