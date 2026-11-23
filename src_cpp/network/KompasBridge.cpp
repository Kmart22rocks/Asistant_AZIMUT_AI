#include "KompasBridge.h"
#include <QNetworkReply>
#include <QNetworkRequest>
#include <QJsonDocument>

KompasBridge::KompasBridge(QObject *parent)
    : QObject(parent),
      m_netManager(new QNetworkAccessManager(this)),
      m_baseUrl("http://127.0.0.1:8765") {}

void KompasBridge::checkStatus() {
    QNetworkRequest req(QUrl(m_baseUrl + "/status"));
    QNetworkReply *reply = m_netManager->get(req);
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        if (reply->error() == QNetworkReply::NoError) {
            QJsonObject obj = QJsonDocument::fromJson(reply->readAll()).object();
            emit statusReceived(obj["indicator"].toString(), obj["text"].toString(), obj["context"].toObject());
        } else {
            emit statusReceived("red", "Сервер Python не отвечает", QJsonObject());
        }
        reply->deleteLater();
    });
}

void KompasBridge::connectKompas() {
    QNetworkRequest req(QUrl(m_baseUrl + "/connect"));
    req.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");
    QNetworkReply *reply = m_netManager->post(req, "{}");
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        if (reply->error() == QNetworkReply::NoError) {
            QJsonObject obj = QJsonDocument::fromJson(reply->readAll()).object();
            emit statusReceived(obj["indicator"].toString(), obj["text"].toString(), obj["context"].toObject());
        } else {
            emit statusReceived("red", "Ошибка подключения", QJsonObject());
        }
        reply->deleteLater();
    });
}

void KompasBridge::disconnectKompas() {
    QNetworkRequest req(QUrl(m_baseUrl + "/disconnect"));
    req.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");
    QNetworkReply *reply = m_netManager->post(req, "{}");
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        if (reply->error() == QNetworkReply::NoError) {
            QJsonObject obj = QJsonDocument::fromJson(reply->readAll()).object();
            emit statusReceived(obj["indicator"].toString(), obj["text"].toString(), obj["context"].toObject());
        }
        reply->deleteLater();
    });
}

void KompasBridge::sendCommand(const QJsonObject &cmd) {
    QNetworkRequest req(QUrl(m_baseUrl + "/execute"));
    req.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");
    QByteArray data = QJsonDocument(cmd).toJson();
    QNetworkReply *reply = m_netManager->post(req, data);
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        if (reply->error() == QNetworkReply::NoError) {
            QJsonObject obj = QJsonDocument::fromJson(reply->readAll()).object();
            bool ok = (obj["status"].toString() == "ok");
            emit commandExecuted(ok, obj["message"].toString(), obj["context"].toObject());
        } else {
            emit commandExecuted(false, "Ошибка связи с сервером КОМПАС", QJsonObject());
        }
        reply->deleteLater();
    });
}