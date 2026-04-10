pipeline {
    agent any

    environment {
        MCT_ENABLE_SMOKE = 'false'
    }

    stages {
        stage('Checkout') {
            steps {
                // Checkout Multi-CI-Tools repo
                checkout scm
                
                // Checkout Maven test project in subdirectory
                dir('java-maven-testing') {
                    checkout(
                        [$class: 'GitSCM',
                         branches: [[name: '*/master']],
                         userRemoteConfigs: [[url: 'https://github.com/manpritsingh-mod/Java-Maven-Testing.git']],
                         changelog: false,
                         poll: false]
                    )
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
                    elif [ -x "target/java-maven-testing/.mvn/maven" ]; then
                        echo "Found Maven wrapper"
                    else
                        echo "WARNING: Maven not in PATH - will attempt to use Maven wrapper from target project"
                        # Don't exit here - Maven wrapper might be available in the target repo
                    fi
                    
                    echo ""
                    echo "✓ Python:"
                    which python3 && python3 --version || (echo "ERROR: Python3 not found"; exit 1)
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
                    dir('java-maven-testing') {
                        sh 'python3 -m multi_ci_tools run --emit-json ci-result.json --emit-summary ci-summary.md'
                    }
                }
            }
        }

        stage('Parse Results') {
            steps {
                script {
                    def resultJson = readFile(file: 'java-maven-testing/ci-result.json')
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
            // Archive all result artifacts
            archiveArtifacts artifacts: 'java-maven-testing/ci-result.json,java-maven-testing/ci-summary.md', allowEmptyArchive: true
            
            // Publish JUnit results from surefire reports
            junit testResults: 'java-maven-testing/target/surefire-reports/*.xml', allowEmptyResults: true
            
            // Archive checkstyle reports if present
            archiveArtifacts artifacts: 'java-maven-testing/target/checkstyle-result.xml', allowEmptyArchive: true
            
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
