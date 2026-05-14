import fs from 'fs';
import path from 'path';
import chalk from 'chalk';
import { GoogleGenerativeAI } from '@google/generative-ai';
import { QdrantClient } from '@qdrant/js-client-rest';

// --- CONFIG & UTILS ---
const AGENTS_DIR = '../agents/active';
const LEDGER_PATH = '../project_ledger/history.json';

const qdrant = new QdrantClient({ url: 'http://localhost:6333' });

async function searchAgentMemories(agentName: string, taskDescription: string) {
  console.log(chalk.blue(`[MEMORY] Searching Qdrant for ${agentName}'s past experience...`));
  // In a real implementation, you'd embed the taskDescription and search the collection
  // return qdrant.search('agent_memories', { vector: taskVector, ... });
  return []; 
}

function getAgent(name: string) {
  const filePath = path.join(AGENTS_DIR, `${name.toLowerCase()}.json`);
  if (!fs.existsSync(filePath)) throw new Error(`Agent ${name} not found.`);
  return JSON.parse(fs.readFileSync(filePath, 'utf-8'));
}

function updateAgentMetrics(name: string, success: boolean) {
  const filePath = path.join(AGENTS_DIR, `${name.toLowerCase()}.json`);
  if (!fs.existsSync(filePath)) return;
  const agent = JSON.parse(fs.readFileSync(filePath, 'utf-8'));
  
  // Simulate evolution
  const delta = success ? 0.5 : -1.5;
  agent.success_rate = Math.min(100, Math.max(0, (agent.success_rate || 90) + delta));
  
  // Randomly mutate status if success rate drops too low
  if (agent.success_rate < 50) {
    agent.evolution = "Degraded";
  } else if (agent.success_rate > 95 && agent.evolution !== "Stable") {
    agent.evolution = "Evolved";
  }

  fs.writeFileSync(filePath, JSON.stringify(agent, null, 2));
}

function logToLedger(entry: any) {
  if (!fs.existsSync(LEDGER_PATH)) return;
  const ledger = JSON.parse(fs.readFileSync(LEDGER_PATH, 'utf-8'));
  ledger.logs.push({
    timestamp: new Date().toISOString(),
    ...entry
  });
  // Keep only last 100 logs
  if (ledger.logs.length > 100) ledger.logs.shift();
  fs.writeFileSync(LEDGER_PATH, JSON.stringify(ledger, null, 2));
}

// --- CORE LOGIC: THE ASEPTIC FREELANCER ---
async function runFreelancerTask(task: string, specialty: string) {
  console.log(chalk.yellow(`\n[GOVERNANCE] Hiring Aseptic Freelancer for: ${specialty}...`));
  
  logToLedger({ type: 'FREELANKER_HIRE', specialty, task });

  // Simulation of Isolation
  const cleanRoom = path.join(process.cwd(), 'temp_freelancer_workspace');
  if (!fs.existsSync(cleanRoom)) fs.mkdirSync(cleanRoom);
  
  console.log(chalk.blue(`[SECURITY] Restricted workspace created at: ${cleanRoom}`));
  console.log(chalk.blue(`[SECURITY] Context restricted to mandatory files only.`));
  
  console.log(chalk.green(`[SUCCESS] Freelancer completed task: ${task}`));
  
  // Cleanup
  fs.rmSync(cleanRoom, { recursive: true, force: true });
}

// --- CORE LOGIC: COMPLIANCE CHECK ---
function checkCompliance(agent: any, action: string): boolean {
  const tier = agent.tier;
  if (action === 'DATABASE_WRITE' && tier < 3) {
    console.log(chalk.red(`[DENIED] Agent ${agent.nome} lacks clearance for Database Write.`));
    logToLedger({ type: 'SECURITY_DENIAL', agent: agent.nome, action });
    return false;
  }
  return true;
}

// --- MAIN ORCHESTRATION ---
async function orchestrate(humanPrompt: string) {
  console.log(chalk.magenta.bold(`\n>>> HUMAN PROXY RECEIVED: "${humanPrompt}"`));
  logToLedger({ type: 'HUMAN_PROMPT', prompt: humanPrompt });

  // 1. Architect (Shadow) analyzes the request
  const shadow = getAgent('Shadow');
  console.log(chalk.cyan(`[ORCHESTRATOR] Delegating analysis to Shadow (${shadow.model})...`));

  // 2. Mocking the break-down
  const subTasks = [
    { name: 'Falcon', task: 'Update README with new project specs', type: 'DOCS' },
    { name: 'Nova', task: 'Implement Dashboard UI component', type: 'CODE' },
    { name: 'Chen', task: 'Optimize MongoDB aggregation pipelines', type: 'CODE' },
    { name: 'FREELANCER', task: 'Verify Payment Gateway Security', type: 'SECURITY' }
  ];

  for (const item of subTasks) {
    if (item.name === 'FREELANCER') {
      await runFreelancerTask(item.task, 'Payment Specialist');
      continue;
    }

    const agent = getAgent(item.name);
    console.log(chalk.white(`\n[ASSIGNMENT] ${agent.nome} (${agent.model}) -> ${item.task}`));
    
    // Memory Retrieval
    await searchAgentMemories(agent.nome, item.task);
    
    console.log(chalk.gray(`[RULESET] Applying ruleset: ${agent.ruleset_version || 'DEFAULT'}`));
    
    // Evolutionary Trait Simulation
    if (agent.evolution === 'Mutating') {
      console.log(chalk.yellow(`[WATCH] Agent ${agent.nome} is in MUTATING state. Monitoring for hallucinations...`));
      if (Math.random() > 0.9) {
        console.log(chalk.red(`[CRITICAL] Hallucination detected in ${agent.nome}. Reverting ruleset to stable version.`));
        updateAgentMetrics(agent.nome, false);
        logToLedger({ type: 'HALLUCINATION', agent: agent.nome, task: item.task });
        continue;
      }
    }

    if (checkCompliance(agent, 'FILE_READ')) {
      console.log(chalk.green(`[SUCCESS] ${agent.nome} delivered update (Score: ${agent.success_rate}%).`));
      updateAgentMetrics(agent.nome, true);
      logToLedger({ type: 'TASK_SUCCESS', agent: agent.nome, task: item.task });
    }
  }

  console.log(chalk.magenta.bold(`\n>>> SQUAD WORK COMPLETE. VERIFICATION LOGGED IN LEDGER.`));
}

// Demo Run
orchestrate("Create the new client portal with secure payment gateway.");
