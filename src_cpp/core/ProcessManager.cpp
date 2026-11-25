#include "ProcessManager.h"
#include <QCoreApplication>
#include <QProcessEnvironment>
#include <QDir>
#include <QDebug>

ProcessManager::ProcessManager(QObject* parent)
    : QObject(parent),
      m_pythonProcess(new QProcess(this)),
      m_ollamaProcess(new QProcess(this)),
      m_serverReadyEmitted(false) {
}

ProcessManager::~ProcessManager() {
    stopServices();
}

void ProcessManager::startServices() {
    m_serverReadyEmitted = false;
    QString projectRoot = "D:/Projects file/CLionProjects/Asistant_AZIMUT_II";
    QString pythonExe = projectRoot + "/.venv/Scripts/python.exe";
    QString serverScript = projectRoot + "/src_python/server.py";
    m_pythonProcess->setWorkingDirectory(projectRoot + "/src_python");
    m_pythonProcess->setProcessChannelMode(QProcess::MergedChannels);
    connect(m_pythonProcess, &QProcess::readyReadStandardOutput, this, [this]() {
        QString out = QString::fromUtf8(m_pythonProcess->readAllStandardOutput());
        qDebug().noquote() << "[PY]" << out.trimmed();
        if (!m_serverReadyEmitted && out.contains("8765")) {
            m_serverReadyEmitted = true;
            emit pythonServerReady();
        }
    });
    m_pythonProcess->start(pythonExe, QStringList() << "-u" << serverScript);

    QProcessEnvironment env = QProcessEnvironment::systemEnvironment();
    env.insert("OLLAMA_VULKAN", "1");
    env.insert("OLLAMA_FLASH_ATTENTION", "1");
    env.insert("OLLAMA_KV_CACHE_TYPE", "q8_0");
    env.insert("OLLAMA_NUM_PARALLEL", "1");
    env.insert("OLLAMA_MAX_LOADED_MODELS", "1");
    env.insert("OLLAMA_KEEP_ALIVE", "-1");
    env.insert("SYCL_CACHE_PERSISTENT", "1");
    m_ollamaProcess->setProcessEnvironment(env);

    QString ollamaExe = "C:/Users/Kmart22rocks/AppData/Local/Programs/Ollama/ollama.exe";
    m_ollamaProcess->start(ollamaExe, QStringList() << "serve");
}

void ProcessManager::unloadModel(const QString& modelName) {
    if (modelName.isEmpty()) return;
    QString ollamaExe = "C:/Users/Kmart22rocks/AppData/Local/Programs/Ollama/ollama.exe";
    QProcess::startDetached(ollamaExe, QStringList() << "stop" << modelName);
}

void ProcessManager::stopServices() {
    QString ollamaExe = "C:/Users/Kmart22rocks/AppData/Local/Programs/Ollama/ollama.exe";
    QProcess::execute(ollamaExe, QStringList() << "stop" << "qwen2.5-coder:14b");
    QProcess::execute(ollamaExe, QStringList() << "stop" << "qwen2.5-coder:7b");
    if (m_pythonProcess->state() != QProcess::NotRunning) {
        m_pythonProcess->kill();
        m_pythonProcess->waitForFinished(2000);
    }
    if (m_ollamaProcess->state() != QProcess::NotRunning) {
        m_ollamaProcess->kill();
        m_ollamaProcess->waitForFinished(2000);
    }
}