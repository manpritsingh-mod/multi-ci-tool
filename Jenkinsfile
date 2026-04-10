pipeline {
    agent any

    environment {
        MCT_ENABLE_SMOKE = 'false'
        JAVA_HOME = '/opt/java/openjdk'  
    }

    tools {
        // jdk 'jdk-17'
        maven 'mvn-3.9'

    stages {
        stage('Checkout') {
            steps {
                // The main Jenkins job checks out the current repo (Java-Maven-Testing) automatically to root.
                checkout scm
                
                // Explicitly Checkout the Python SDK into a subdirectory
                dir('multi-ci-tools') {
                    git branch: 'main', url: 'https://github.com/manpritsingh-mod/multi-ci-tool.git'
                }
            }
        }

        stage('Preflight Checks') {
            steps {
                sh '''
                    echo "Checking prerequisites..."
                    echo "✓ Java:"
                    which java && java -version || (echo "ERROR: Java not found"; exit 1)
                    
                    echo ""
                    echo "✓ Maven (checking system or mvnw):"
                    if which mvn > /dev/null 2>&1; then
                        mvn --version
                    elif [ -x ".mvn/maven" ]; then
                        echo "Found Maven wrapper"
                    else
                        echo "WARNING: Maven not in PATH - will attempt to use Maven wrapper from target project"
                    fi
                '''
            }
        }

        stage('Install Python & SDK') {
            steps {
                sh '''
                    echo "Installing Astral uv (Python manager)..."
                    curl -LsSf https://astral.sh/uv/install.sh | sh
                    export PATH="$HOME/.local/bin:$PATH"
                    
                    echo "Bootstrapping Python 3.10 user-space environment..."
                    uv venv .venv --python 3.10
                    
                    echo "Installing SDK..."
                    . .venv/bin/activate
                    uv pip install -e ./multi-ci-tools
                '''
            }
        }

        stage('Run Multi-CI-Tools Pipeline') {
            steps {
                // We are at the root, which is Java-Maven-Testing
                sh '''
                    export PATH="$HOME/.local/bin:$PATH"
                    . .venv/bin/activate
                    python -m multi_ci_tools run --emit-json ci-result.json --emit-summary ci-summary.md
                '''
            }
        }

        stage('Parse Results') {
            steps {
                script {
                    // Use Python to safely extract the 'overall' status without relying on Pipeline Utility Steps plugin
                    def status = sh(script: '''
                        export PATH="$HOME/.local/bin:$PATH"
                        . .venv/bin/activate
                        python -c "import json, sys; sys.stdout.write(json.load(open('ci-result.json'))['overall'].upper())"
                    ''', returnStdout: true).trim()

                    echo "Pipeline overall status evaluated: ${status}"
                    
                    // Map SDK overall status to Jenkins build state
                    if (status == 'PASS') {
                        echo "✅ Build PASSED"
                        currentBuild.result = 'SUCCESS'
                    } else if (status == 'WARN') {
                        echo "⚠️ Build completed with WARNINGS"
                        unstable('Build completed with warnings')
                    } else if (status == 'FAIL') {
                        echo "❌ Build FAILED"
                        currentBuild.result = 'FAILURE'
                    } else {
                        echo "⚠️ Unknown status: ${status}"
                        unstable('Unknown build status')
                    }
                }
            }
        }
    }

    post {
        always {
            // Archive all result artifacts from the root
            archiveArtifacts artifacts: 'ci-result.json,ci-summary.md', allowEmptyArchive: true
            
            // Publish JUnit results from surefire reports
            junit testResults: 'target/surefire-reports/*.xml', allowEmptyResults: true
            
            // Archive checkstyle reports if present
            archiveArtifacts artifacts: 'target/checkstyle-result.xml', allowEmptyArchive: true
            
            echo "Pipeline execution complete."
        }
        
        failure {
            echo "❌ Pipeline failed! Check logs and artifacts above."
        }
        
        success {
            echo "✅ Pipeline succeeded!"
        }
    }
}
