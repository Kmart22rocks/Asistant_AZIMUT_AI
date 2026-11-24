#pragma once
#include <QObject>
#include <QNetworkAccessManager>
#include <QJsonObject>
#include <QJsonArray>
#include <QStringList>

class KompasBridge : public QObject {
    Q_OBJECT
public:
    explicit KompasBridge(QObject* parent = nullptr);

    void checkStatus();
    void connectKompas();
    void disconnectKompas();
    void executeCommands(const QJsonObject& payload);

    signals:
        void statusReceived(bool connected, bool docOpen, const QString& docName, const QString& message);
    void executionFinished(bool success, const QString& message, const QStringList& logs);
    void contextUpdated(const QJsonArray& features, const QJsonObject& selection, const QJsonArray& nativeTree);
    void bridgeError(const QString& errorMsg);

private:
    void parseStatusObject(const QJsonObject& obj);
    QNetworkAccessManager* m_net;
    QString m_baseUrl;
};