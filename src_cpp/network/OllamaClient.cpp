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

void OllamaClient::setModelName(const QString& modelName) {
    m_modelName = modelName;
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
        "Правила:\n"
        "1. Если пользователю не хватает обязательных размеров для нового построения, верни:\n"
        "{\"status\":\"clarify\",\"question\":\"Вежливый вопрос на русском языке\"}\n"
        "2. Если размеры понятны или это изменение/удаление/отмена, верни:\n"
        "{\"status\":\"execute\",\"reply\":\"Краткий ответ на русском\",\"commands\":[{\"action\":\"build|update|delete|undo|clear\",\"id\":\"уникальный_id\",\"type\":\"тип\",\"params\":{...}}]}\n"
        "3. Доступные типы (type) и их параметры (params):\n"
        "- plate / box: {\"width\":W, \"length\":L, \"thickness\":T}\n"
        "- cube: {\"size\":S}\n"
        "- cylinder: {\"diameter\":D, \"height\":H, \"x\":0, \"y\":0}\n"
        "- tube: {\"outer_diameter\":D, \"inner_diameter\":d, \"height\":H}\n"
        "- polygon: {\"sides\":N, \"diameter\":D, \"height\":H}\n"
        "- cone: {\"diameter\":D, \"top_diameter\":0, \"height\":H}\n"
        "- sphere: {\"diameter\":D, \"x\":0, \"y\":0}\n"
        "- slot: {\"length\":L, \"width\":W, \"depth\":H, \"is_cut\":true, \"through\":false}\n"
        "- profile: {\"points\":[[x1,y1],[x2,y2],...], \"height\":H, \"is_cut\":false}\n"
        "- hole: {\"diameter\":D, \"x\":0, \"y\":0, \"through\":true, \"depth\":10}\n"
        "- holes_corner: {\"diameter\":D, \"offset\":O, \"plate_width\":W, \"plate_length\":L}\n"
        "- holes_circ: {\"count\":N, \"diameter\":d, \"circle_diameter\":D}\n"
        "- cut_box: {\"width\":W, \"length\":L, \"depth\":H, \"x\":0, \"y\":0, \"through\":false}\n"
        "- chamfer: {\"distance\":C}\n"
        "- fillet: {\"radius\":R}\n"
        "4. Если пользователь просит изменить существующий элемент, используй action=\"update\" и его id из списка элементов ИИ.\n"
        "5. Если пользователь просит добавить новый элемент (фаску, скругление, отверстие, цилиндр), всегда используй action=\"build\".\n"
        "6. Если пользователь просит отменить шаг — action=\"undo\". Если очистить всю деталь — action=\"clear\"."
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
            QString replyText = obj.value("reply").toString("Выполняю построение в КОМПАС-3D.");
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