#pragma once
#include <QObject>
#include <QNetworkAccessManager>
#include <QJsonObject>
#include <QJsonArray>

class OllamaClient : public QObject {
    Q_OBJECT
public:
    explicit OllamaClient(QObject *parent = nullptr);
    void askAgent(const QString &userText, const QJsonObject &cadContext);

    signals:
        void clarificationNeeded(const QString &question);
    void commandsReady(const QString &replyText, const QJsonObject &batchPayload);
    void errorOccurred(const QString &errorMsg);

private:
    QNetworkAccessManager *m_netManager;
    QString m_lastQuestion;
    QString m_pendingUserText;
};