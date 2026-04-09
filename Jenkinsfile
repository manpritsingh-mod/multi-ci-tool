pipeline {
    agent any

    environment {
        MCT_ENABLE_SMOKE = 'false'
        // Add the local user bin directory to PATH so we can invoke pip and multi-ci-tools
        PATH = "${env.WORKSPACE}/.local/bin:${env.HOME}/.local/bin:${env.PATH}"
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }
        
        stage('Setup Dependencies (No Docker)') {
            steps {
                echo "Installing PIP directly via Python bootstrap because Docker and apt-get root access are unavailable..."
                // Download the official pip bootstrap script
                sh 'curl -sS https://bootstrap.pypa.io/get-pip.py -o get-pip.py'
                
                // Install pip to the current Jenkins user's home directory
                sh 'python3 get-pip.py --user'
                
                // Install our newly written SDK package locally
                sh 'python3 -m pip install --user --upgrade pip'
                sh 'python3 -m pip install --user -e .'
            }
        }

        stage('Test CI Adapter Detection') {
            steps {
                echo 'Running inspect-env to verify JenkinsAdapter detects the CI context successfully'
                sh 'python3 -m multi_ci_tools inspect-env'
            }
        }

        stage('Test Pipeline Dry Run') {
            steps {
                echo 'Running dry-run to verify pipeline scaffolding'
                sh 'python3 -m multi_ci_tools dry-run'
            }
        }
    }
    
    post {
        always {
            echo "Jenkins Pipeline test complete."
        }
    }
}
