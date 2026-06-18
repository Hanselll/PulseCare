import jenkins.model.Jenkins
import org.jenkinsci.plugins.workflow.cps.CpsFlowDefinition
import org.jenkinsci.plugins.workflow.job.WorkflowJob

def jenkins = Jenkins.get()
def jobName = "PulseCare-Local-CI"
def workspace = System.getenv("PULSECARE_WORKSPACE") ?: "/workspace"
def jenkinsfile = new File("${workspace}/Jenkinsfile")
def pipelineScript = jenkinsfile.exists()
  ? jenkinsfile.text
  : "pipeline { agent any; stages { stage('Missing Jenkinsfile') { steps { error 'Jenkinsfile not found at ${workspace}/Jenkinsfile' } } } }"

def job = jenkins.getItem(jobName)

if (job == null) {
  job = jenkins.createProject(WorkflowJob, jobName)
  job.setDescription("Local PulseCare CI: unit tests, Docker Compose build, stack startup, and health checks.")
}

job.setDefinition(new CpsFlowDefinition(pipelineScript, true))
job.save()
