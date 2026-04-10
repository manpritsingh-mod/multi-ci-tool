pipeline {
    agent any

    environment {
        MCT_ENABLE_SMOKE = 'false'
        JAVA_HOME = '/opt/java/openjdk'  
    }

    tools {
        // jdk 'jdk-17'
        maven 'mvn-3.9'
    tools {
        maven 'mvn-3.9'
    }

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
                    def resultJson = readFile(file: 'ci-result.json')
                    def result = readJSON text: resultJson

                    echo "Pipeline overall status: ${result.overall}"
                    
                    // Map overall status to Jenkins build state
                    if (result.overall == 'pass' || result.overall == 'PASS') {
                        echo "✅ Build PASSED"
                        currentBuild.result = 'SUCCESS'
                    } else if (result.overall == 'warn' || result.overall == 'WARN') {
                        echo "⚠️ Build completed with WARNINGS"
                        unstable('Build completed with warnings')
                    } else if (result.overall == 'fail' || result.overall == 'FAIL') {
                        echo "❌ Build FAILED"
                        currentBuild.result = 'FAILURE'
                    } else {
                        echo "⚠️ Unknown status: ${result.overall}"
                        unstable('Unknown build status')
                    }

                    // Print stage details
                    echo "\n=== Stage Results ==="
                    result.stages.each { stage ->
                        echo "${stage.name}: ${stage.status} (${stage.duration_seconds}s)"
                    }

                    // Print test summary if available
                    if (result.test_summary) {
                        echo "\n=== Test Summary ==="
                        echo "Total: ${result.test_summary.total}"
                        echo "Passed: ${result.test_summary.passed}"
                        echo "Failed: ${result.test_summary.failed}"
                        echo "Skipped: ${result.test_summary.skipped}"
                    }

                    // Print lint summary if available
                    if (result.lint_summary) {
                        echo "\n=== Lint Summary ==="
                        echo "Total Violations: ${result.lint_summary.total_violations}"
                        echo "Errors: ${result.lint_summary.errors}"
                        echo "Warnings: ${result.lint_summary.warnings}"
                        echo "Infos: ${result.lint_summary.infos}"
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
