pipeline {
    agent {
        docker {
            image 'maven:3.9-eclipse-temurin-21'
            args '-v /var/run/docker.sock:/var/run/docker.sock'
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

        stage('Preflight Checks') {
            steps {
                sh '''
                    python3 --version
                    mvn --version
                    java -version
                '''
            }
        }

        stage('Install SDK') {
            steps {
                sh '''
                    python3 -m pip install --upgrade pip setuptools
                    pip3 install -e .
                '''
            }
        }

        stage('Run Multi-CI-Tools Pipeline') {
            steps {
                script {
                    sh 'python3 -m multi_ci_tools run --emit-json ci-result.json --emit-summary ci-summary.md'
                }
            }
        }

        stage('Parse Results') {
            steps {
                script {
                    def resultJson = readFile(file: 'ci-result.json')
                    def result = readJSON text: resultJson

                    echo "Pipeline overall status: ${result.overall}"
                    
                    // Map overall status to Jenkins build state
                    if (result.overall == 'pass') {
                        echo "✅ Build PASSED"
                    } else if (result.overall == 'warn') {
                        echo "⚠️ Build completed with WARNINGS"
                        unstable('Build completed with warnings')
                    } else if (result.overall == 'fail') {
                        echo "❌ Build FAILED"
                        currentBuild.result = 'FAILURE'
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
            // Archive all result artifacts
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
