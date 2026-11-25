#pragma once

#include <QObject>
#include <QNetworkAccessManager>
#include <QNetworkReply>
#include <QJsonObject>
#include <QJsonArray>
#include <QTimer>

class OllamaClient : public QObject {
    Q_OBJECT
public:
    explicit OllamaClient(QObject *parent = nullptr);

    void checkConnection();
    void setModelName(const QString &model);
    QString modelName() const;
    void clearHistory();
    void sendPrompt(const QString &userPrompt);

public slots:
    void updateContext(const QJsonArray &features, const QJsonObject &selection, const QJsonArray &tree);

    signals:
        void statusChanged(bool online);
    void clarificationNeeded(const QString &question);
    void commandsReady(const QString &replyText, const QJsonObject &payload);
    void errorOccurred(const QString &error);

private slots:
    void onCheckFinished();
    void onReplyFinished();

private:
    QString buildSystemPrompt() const;

    QNetworkAccessManager *m_nam;
    QString m_baseUrl;
    QString m_modelName;
    QTimer *m_pingTimer;
    bool m_isOnline;
    QJsonObject m_currentContext;
    QJsonArray m_history;
    QString m_lastUserPrompt;
};