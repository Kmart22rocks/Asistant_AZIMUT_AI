#include "OllamaClient.h"
#include <QNetworkRequest>
#include <QNetworkReply>
#include <QJsonDocument>

OllamaClient::OllamaClient(QObject *parent)
    : QObject(parent),
      m_netManager(new QNetworkAccessManager(this)) {}

void OllamaClient::askAgent(const QString &userText, const QJsonObject &cadContext) {
    QString combinedInput = userText;
    if (!m_pendingUserText.isEmpty()) {
        combinedInput = m_pendingUserText + ". Уточнение пользователя: " + userText;
    }

    QString systemPrompt =
        "Ты CAD-агент АЗИМУТ для КОМПАС-3D. Отвечай ТОЛЬКО валидным JSON.\n"
        "Доступные действия (action):\n"
        "- 'build': создать новый элемент.\n"
        "- 'update': изменить размеры существующего элемента из контекста.\n"
        "- 'delete': удалить конкретный элемент (укажи его id или type из контекста).\n"
        "- 'undo': отменить последний сделанный шаг (params не нужны).\n"
        "- 'clear': удалить все элементы и очистить деталь.\n"
        "Каталог типов (type и params):\n"
        "1) 'cube' (куб): size.\n"
        "2) 'box' (брусок/параллелепипед): width, length, height.\n"
        "3) 'plate' (пластина): width, length, thickness.\n"
        "4) 'cylinder' (цилиндр/бобышка/стойка): diameter, height, x(0), y(0).\n"
        "5) 'tube' (втулка/труба): outer_diameter, inner_diameter, height, x(0), y(0).\n"
        "6) 'polygon' (многогранник/шестигранник, НЕ куб): sides, diameter, height, x(0), y(0).\n"
        "7) 'cone' (конус): base_diameter, top_diameter(0), height, x(0), y(0).\n"
        "8) 'hole' (одиночное отверстие): diameter, depth(0 если сквозное), x(0), y(0).\n"
        "9) 'corner_holes' (4 отверстия по углам): diameter, offset.\n"
        "10) 'circle_holes' (отверстия по окружности): count, diameter, circle_diameter, x(0), y(0).\n"
        "11) 'cut_box' (прямоугольный паз/вырез): width, length, depth(0), x(0), y(0).\n"
        "12) 'chamfer' (фаска): distance.\n"
        "13) 'fillet' (скругление): radius.\n"
        "Если для 'build' не указан главный размер, верни:\n"
        "{\"status\":\"clarify\",\"question\":\"Короткий вопрос на русском\"}\n"
        "Иначе верни:\n"
        "{\"status\":\"execute\",\"reply\":\"Краткий ответ на русском\",\"commands\":[{\"action\":\"undo\"}]}";

    QString contextStr = QString::fromUtf8(QJsonDocument(cadContext).toJson(QJsonDocument::Compact));
    QString fullPrompt = "Контекст детали: " + contextStr + "\nЗапрос: " + combinedInput;

    QJsonObject reqBody;
    reqBody["model"] = "qwen2.5-coder:7b";
    reqBody["system"] = systemPrompt;
    reqBody["prompt"] = fullPrompt;
    reqBody["stream"] = false;
    reqBody["format"] = "json";

    QJsonObject options;
    options["temperature"] = 0.1;
    reqBody["options"] = options;

    QNetworkRequest req(QUrl("http://127.0.0.1:11434/api/generate"));
    req.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");

    QNetworkReply *reply = m_netManager->post(req, QJsonDocument(reqBody).toJson());
    connect(reply, &QNetworkReply::finished, this, [this, reply, combinedInput]() {
        if (reply->error() != QNetworkReply::NoError) {
            emit errorOccurred("Ошибка связи с Ollama: " + reply->errorString());
            reply->deleteLater();
            return;
        }

        QJsonObject outer = QJsonDocument::fromJson(reply->readAll()).object();
        QString rawResponse = outer["response"].toString();
        QJsonObject aiJson = QJsonDocument::fromJson(rawResponse.toUtf8()).object();

        QString status = aiJson["status"].toString();
        if (status == "clarify") {
            m_pendingUserText = combinedInput;
            emit clarificationNeeded(aiJson["question"].toString());
        } else if (status == "execute") {
            m_pendingUserText.clear();
            QJsonObject payload;
            payload["commands"] = aiJson["commands"].toArray();
            emit commandsReady(aiJson["reply"].toString(), payload);
        } else {
            emit errorOccurred("Некорректный ответ модели: " + rawResponse);
        }
        reply->deleteLater();
    });
}