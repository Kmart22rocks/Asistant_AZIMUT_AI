#include "KompasBridge.h"
#include <QNetworkRequest>
#include <QNetworkReply>
#include <QJsonDocument>
#include <QUrl>

KompasBridge::KompasBridge(QObject* parent)
    : QObject(parent),
      m_net(new QNetworkAccessManager(this)),
      m_baseUrl("http://127.0.0.1:8765") {
}

void KompasBridge::parseStatusObject(const QJsonObject& obj) {
    bool connected = obj.value("connected").toBool(false);
    bool docOpen = obj.value("doc_open").toBool(false);
    QString docName = obj.value("doc_name").toString();
    QString msg = obj.value("message").toString();

    emit statusReceived(connected, docOpen, docName, msg);

    QJsonArray features = obj.value("features").toArray();
    QJsonObject selection = obj.value("selection").toObject();
    QJsonArray nativeTree = obj.value("native_tree").toArray();
    emit contextUpdated(features, selection, nativeTree);
}

void KompasBridge::checkStatus() {
    QNetworkRequest req(QUrl(m_baseUrl + "/status"));
    QNetworkReply* reply = m_net->get(req);
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        if (reply->error() == QNetworkReply::NoError) {
            QJsonDocument doc = QJsonDocument::fromJson(reply->readAll());
            if (doc.isObject()) {
                parseStatusObject(doc.object());
            }
        }
        reply->deleteLater();
    });
}

void KompasBridge::connectKompas() {
    QNetworkRequest req(QUrl(m_baseUrl + "/connect"));
    QNetworkReply* reply = m_net->get(req);
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        QByteArray raw = reply->readAll();
        QJsonDocument doc = QJsonDocument::fromJson(raw);
        if (doc.isObject()) {
            QJsonObject obj = doc.object();
            parseStatusObject(obj);
            if (!obj.value("connected").toBool(false)) {
                emit bridgeError(obj.value("message").toString("Не удалось подключиться к КОМПАС-3D"));
            }
        } else if (reply->error() != QNetworkReply::NoError) {
            emit bridgeError(reply->errorString());
        }
        reply->deleteLater();
    });
}

void KompasBridge::disconnectKompas() {
    QNetworkRequest req(QUrl(m_baseUrl + "/disconnect"));
    QNetworkReply* reply = m_net->get(req);
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        if (reply->error() == QNetworkReply::NoError) {
            QJsonDocument doc = QJsonDocument::fromJson(reply->readAll());
            if (doc.isObject()) {
                parseStatusObject(doc.object());
            }
        }
        reply->deleteLater();
    });
}

void KompasBridge::executeCommands(const QJsonObject& payload) {
    QNetworkRequest req(QUrl(m_baseUrl + "/execute"));
    req.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");
    QByteArray body = QJsonDocument(payload).toJson(QJsonDocument::Compact);

    QNetworkReply* reply = m_net->post(req, body);
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        QByteArray raw = reply->readAll();
        QJsonDocument doc = QJsonDocument::fromJson(raw);
        if (doc.isObject()) {
            QJsonObject obj = doc.object();
            bool ok = obj.value("success").toBool(false);
            QString msg = obj.value("message").toString();
            QStringList logs;
            for (const QJsonValue& v : obj.value("logs").toArray()) {
                logs.append(v.toString());
            }
            if (obj.contains("status") && obj.value("status").isObject()) {
                parseStatusObject(obj.value("status").toObject());
            }
            emit executionFinished(ok, msg, logs);
        } else {
            emit bridgeError(reply->errorString());
        }
        reply->deleteLater();
    });
}