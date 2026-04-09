pipeline {
    agent any

    environment {
        // Mocking an environment variable to ensure Jenkins capabilities are used safely
        MCT_ENABLE_SMOKE = 'false'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }
        
        stage('Setup Python Env') {
            steps {
                // Ensure pip is available and install the SDK in editable mode
                sh 'python -m pip install --upgrade pip || true'
                sh 'pip install -e .'
            }
        }

        stage('Test CI Adapter Detection') {
            steps {
                echo 'Running inspect-env to verify JenkinsAdapter detects the CI context successfully'
                sh 'python -m multi_ci_tools inspect-env'
            }
        }

        stage('Test Pipeline Dry Run') {
            steps {
                echo 'Running dry-run to verify pipeline scaffolding'
                sh 'python -m multi_ci_tools dry-run'
            }
        }
    }
    
    post {
        always {
            echo "Jenkins Pipeline test complete."
        }
    }
}
