#pragma once
#include <QObject>
#include <QNetworkAccessManager>
#include <QJsonObject>
#include <QJsonArray>

class OllamaClient : public QObject {
    Q_OBJECT
public:
    explicit OllamaClient(QObject* parent = nullptr);

    void sendPrompt(const QString& userText);
    void updateContext(const QJsonArray& features, const QJsonObject& selection, const QJsonArray& nativeTree);
    void setModelName(const QString& modelName);
    void unloadModelFromMemory(const QString& modelName);
    QString modelName() const;

    signals:
        void clarificationNeeded(const QString& question);
    void commandsReady(const QString& replyText, const QJsonObject& payload);
    void errorOccurred(const QString& errorMsg);

private:
    QString buildSystemPrompt() const;
    QNetworkAccessManager* m_net;
    QJsonArray m_currentFeatures;
    QJsonObject m_currentSelection;
    QJsonArray m_nativeTree;
    QString m_pendingUserText;
    QString m_modelName;
};