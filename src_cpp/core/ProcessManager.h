#pragma once
#include <QObject>
#include <QProcess>

class ProcessManager : public QObject {
    Q_OBJECT
public:
    explicit ProcessManager(QObject* parent = nullptr);
    ~ProcessManager() override;

    void startServices();
    void stopServices();
    void unloadModel(const QString& modelName);

    signals:
        void pythonServerReady();

private:
    QProcess* m_pythonProcess;
    QProcess* m_ollamaProcess;
    bool m_serverReadyEmitted = false;
};