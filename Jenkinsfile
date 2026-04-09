pipeline {
    agent {
        docker { 
            image 'maven:3.9-eclipse-temurin-17'
            // Run as root to allow apt-get install
            args '-u root' 
        }
    }

    environment {
        MCT_ENABLE_SMOKE = 'false'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }
        
        stage('Setup Python Environment') {
            steps {
                // The maven image doesn't have python installed natively
                sh 'apt-get update && apt-get install -y python3 python3-pip python3-venv'
                
                // Create a virtual environment to safely isolate pip installs
                sh 'python3 -m venv /tmp/venv'
                
                // Install our newly written SDK package securely inside the venv
                sh '/tmp/venv/bin/python3 -m pip install --upgrade pip || true'
                sh '/tmp/venv/bin/pip install -e .'
            }
        }

        stage('Test CI Adapter Detection') {
            steps {
                echo 'Running inspect-env to verify JenkinsAdapter detects the CI context successfully'
                sh '/tmp/venv/bin/python3 -m multi_ci_tools inspect-env'
            }
        }

        stage('Test Pipeline Dry Run') {
            steps {
                echo 'Running dry-run to verify pipeline scaffolding'
                sh '/tmp/venv/bin/python3 -m multi_ci_tools dry-run'
            }
        }
    }
    
    post {
        always {
            echo "Jenkins Pipeline test complete."
        }
    }
}
