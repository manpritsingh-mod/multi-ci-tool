pipeline {
    agent any

    environment {
        MCT_ENABLE_SMOKE = 'false'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }
        
        stage('Test Pipeline with ShiningPanda') {
            steps {
                // You must configure a Python installation named "Python3" 
                // in Manage Jenkins -> Global Tool Configuration.
                withPythonEnv('Python3') {
                    echo "Installing SDK..."
                    sh 'python -m pip install --upgrade pip'
                    sh 'pip install -e .'
                    
                    echo 'Running inspect-env to verify JenkinsAdapter...'
                    sh 'python -m multi_ci_tools inspect-env'
                    
                    echo 'Running dry-run to verify pipeline scaffolding...'
                    sh 'python -m multi_ci_tools dry-run'
                }
            }
        }
    }
    
    post {
        always {
            echo "Jenkins Pipeline test complete."
        }
    }
}
