#pragma once
#include <QObject>
#include <QNetworkAccessManager>
#include <QJsonObject>

class KompasBridge : public QObject {
    Q_OBJECT
public:
    explicit KompasBridge(QObject *parent = nullptr);

    void checkStatus();
    void connectKompas();
    void disconnectKompas();
    void sendCommand(const QJsonObject &cmd);

    signals:
        void statusReceived(const QString &indicator, const QString &text, const QJsonObject &context);
    void commandExecuted(bool success, const QString &message, const QJsonObject &context);

private:
    QNetworkAccessManager *m_netManager;
    QString m_baseUrl;
};