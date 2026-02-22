"""
Offenes Leuchten – Autonomy Loop
=================================
Ilija kann jetzt eigenständig auf ein Ziel hinarbeiten:

    Ziel setzen → Plan erstellen → Skills ausführen
    → Ergebnis evaluieren → weiterarbeiten bis Ziel erreicht

Ablauf:
    1. User setzt ein Ziel (natural language)
    2. Planner-LLM erstellt einen strukturierten Plan (JSON)
    3. Executor führt Schritt für Schritt Skills aus
    4. Evaluator bewertet: Ziel erreicht? Nächster Schritt? Fehler?
    5. Loop läuft bis: Ziel erreicht | Max-Iterationen | Nutzer abbricht
"""

import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Optional, Dict, Any

from skill_policy import get_policy, ExecutionMode, PolicyDecision

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Datenstrukturen
# ---------------------------------------------------------------------------

class StepStatus(Enum):
    PENDING   = "pending"
    RUNNING   = "running"
    DONE      = "done"
    FAILED    = "failed"
    SKIPPED   = "skipped"


class LoopStatus(Enum):
    IDLE          = "idle"
    PLANNING      = "planning"
    EXECUTING     = "executing"
    EVALUATING    = "evaluating"
    GOAL_REACHED  = "goal_reached"
    GOAL_FAILED   = "goal_failed"
    ABORTED       = "aborted"


@dataclass
class PlanStep:
    index:       int
    description: str               # Was soll in diesem Schritt passieren?
    skill:       Optional[str]     # Welcher Skill soll genutzt werden?
    params:      Dict[str, Any]    # Parameter für den Skill
    reason:      str               # Warum dieser Schritt?
    status:      StepStatus = StepStatus.PENDING
    result:      Optional[str] = None
    error:       Optional[str] = None


@dataclass
class GoalSession:
    goal:          str
    plan:          List[PlanStep] = field(default_factory=list)
    history:       List[Dict]     = field(default_factory=list)   # Ausführungs-Log
    status:        LoopStatus     = LoopStatus.IDLE
    iteration:     int            = 0
    final_summary: Optional[str]  = None


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

PLANNER_SYSTEM_PROMPT = """Du bist Ilijias Planner-Modul. Deine Aufgabe:
Ein komplexes Ziel in konkrete, ausführbare Schritte zerlegen.

Verfügbare Skills:
{skills}

Antworte NUR mit diesem JSON-Format:
{{
  "goal_understood": "Dein Verständnis des Ziels in einem Satz",
  "plan": [
    {{
      "index": 0,
      "description": "Was wird in diesem Schritt getan",
      "skill": "skill_name_oder_null",
      "params": {{"param1": "wert1"}},
      "reason": "Warum ist dieser Schritt nötig?"
    }}
  ],
  "estimated_steps": 3
}}

Regeln:
- Maximal 8 Schritte pro Plan
- Nutze nur Skills die in der Liste stehen
- Wenn kein passender Skill existiert, setze "skill": "skill_erstellen" und beschreibe was der neue Skill tun soll
- params muss immer ein Objekt sein, niemals null
- Sei präzise: lieber 3 klare Schritte als 8 vage"""


EVALUATOR_SYSTEM_PROMPT = """Du bist Ilijias Evaluator-Modul. Bewerte den Fortschritt.

Ursprüngliches Ziel: {goal}

Bisherige Schritte:
{steps_summary}

Letztes Ergebnis:
{last_result}

Antworte NUR mit diesem JSON:
{{
  "goal_reached": true/false,
  "assessment": "Kurze Bewertung was erreicht wurde",
  "next_action": "continue|retry|replan|abort",
  "reason": "Warum diese Entscheidung?",
  "retry_hint": "Falls retry: was soll anders gemacht werden?"
}}

Entscheidungsregeln:
- goal_reached=true → Loop ist erfolgreich abgeschlossen
- next_action=continue → nächster Schritt im Plan
- next_action=retry → diesen Schritt mit Anpassung nochmal
- next_action=replan → Plan ist gescheitert, neuen Plan erstellen
- next_action=abort → Ziel nicht erreichbar, aufgeben"""


SUMMARY_SYSTEM_PROMPT = """Du bist Ilija. Fasse das Ergebnis einer autonomen Aufgabe zusammen.

Ziel: {goal}
Status: {status}

Ausgeführte Schritte:
{steps_summary}

Schreibe eine klare, freundliche Zusammenfassung für den User:
- Was wurde erreicht?
- Was hat funktioniert?
- Was (falls vorhanden) ist noch offen?
Antworte in 2-4 Sätzen, direkt auf Deutsch."""


# ---------------------------------------------------------------------------
# Hauptklasse
# ---------------------------------------------------------------------------

class AutonomyLoop:
    """
    Führt Ilija in einem autonomen Ziel-Plan-Ausführ-Evaluier-Zyklus.

    Verwendung:
        loop = AutonomyLoop(kernel)
        result = loop.run("Erstelle eine Python-Datei mit den ersten 10 Primzahlen")
    """

    def __init__(self, kernel, max_iterations: int = 10, verbose: bool = True):
        """
        kernel:         CloudKernel-Instanz (hat provider, manager, etc.)
        max_iterations: Sicherheits-Limit für Ausführungsschritte
        verbose:        Fortschritt im Terminal ausgeben
        """
        self.kernel        = kernel
        self.max_iterations = max_iterations
        self.verbose       = verbose
        self.session: Optional[GoalSession] = None
        self._abort_flag   = False

    # -----------------------------------------------------------------------
    # Öffentliche API
    # -----------------------------------------------------------------------

    def run(self, goal: str) -> GoalSession:
        """
        Startet einen vollständigen autonomen Lauf für das gegebene Ziel.
        Gibt die abgeschlossene GoalSession zurück.
        """
        self._abort_flag = False
        self.session = GoalSession(goal=goal)

        self._log(f"\n🎯 Ziel: {goal}")
        self._log("─" * 60)

        # Phase 1: Plan erstellen
        self.session.status = LoopStatus.PLANNING
        plan = self._create_plan(goal)

        if not plan:
            self.session.status = LoopStatus.GOAL_FAILED
            self.session.final_summary = "Konnte keinen Plan erstellen."
            return self.session

        self.session.plan = plan
        self._log(f"\n📋 Plan erstellt ({len(plan)} Schritte):")
        for step in plan:
            skill_info = f"[{step.skill}]" if step.skill else "[direkt]"
            self._log(f"   {step.index + 1}. {step.description}  {skill_info}")

        # Phase 2: Ausführungsschleife
        self.session.status = LoopStatus.EXECUTING
        current_step_idx = 0
        replan_count     = 0
        step_retry_count = 0   # Zähler: wie oft wurde der aktuelle Schritt wiederholt
        MAX_STEP_RETRIES = 3   # Nach 3 Retries → replan statt endlos wiederholen

        while current_step_idx < len(self.session.plan):

            # Sicherheits-Abbruch
            if self._abort_flag:
                self.session.status = LoopStatus.ABORTED
                break
            if self.session.iteration >= self.max_iterations:
                self._log(f"\n⚠️  Maximale Iterationen ({self.max_iterations}) erreicht.")
                self.session.status = LoopStatus.GOAL_FAILED
                break

            step = self.session.plan[current_step_idx]
            step.status = StepStatus.RUNNING
            self.session.iteration += 1

            self._log(f"\n▶️  Schritt {step.index + 1}/{len(self.session.plan)}: {step.description}")
            if step.skill:
                self._log(f"   🔧 Skill: {step.skill}  |  Params: {step.params}")

            # Skill ausführen
            result = self._execute_step(step)
            step.result = result

            # Log-Eintrag
            self.session.history.append({
                "step":        step.index,
                "description": step.description,
                "skill":       step.skill,
                "params":      step.params,
                "result":      result,
                "iteration":   self.session.iteration,
            })

            self._log(f"   📤 Ergebnis: {str(result)[:200]}")

            # Phase 3: Evaluieren
            self.session.status = LoopStatus.EVALUATING
            evaluation = self._evaluate(goal, step, result)

            if evaluation.get("goal_reached"):
                step.status = StepStatus.DONE
                self.session.status = LoopStatus.GOAL_REACHED
                self._log("\n✅ Ziel erreicht!")
                break

            next_action = evaluation.get("next_action", "continue")
            reason      = evaluation.get("reason", "")
            self._log(f"   🧠 Evaluierung: {next_action} – {reason}")

            if next_action == "continue":
                step.status = StepStatus.DONE
                current_step_idx += 1
                step_retry_count = 0   # Reset Retry-Zähler für nächsten Schritt
                self.session.status = LoopStatus.EXECUTING

            elif next_action == "retry":
                step_retry_count += 1

                # Zu viele Retries für diesen Schritt → replan
                if step_retry_count >= MAX_STEP_RETRIES:
                    self._log(f"   ⚠️  {MAX_STEP_RETRIES} Retries für Schritt {step.index+1} – erzwinge Replan.")
                    step.status = StepStatus.FAILED
                    step_retry_count = 0
                    replan_count += 1
                    if replan_count > 2:
                        self._log("   ❌ Zu viele Replanning-Versuche – breche ab.")
                        self.session.status = LoopStatus.GOAL_FAILED
                        break
                    self.session.status = LoopStatus.PLANNING
                    new_plan = self._create_plan(
                        goal,
                        context=f"Schritt '{step.description}' schlug {MAX_STEP_RETRIES}x fehl. Wähle einen anderen Ansatz."
                    )
                    if new_plan:
                        self.session.plan = new_plan
                        current_step_idx = 0
                        self.session.status = LoopStatus.EXECUTING
                    else:
                        self.session.status = LoopStatus.GOAL_FAILED
                        break
                    continue

                step.status = StepStatus.FAILED
                hint = evaluation.get("retry_hint", "")
                self._log(f"   🔁 Retry {step_retry_count}/{MAX_STEP_RETRIES}: {hint}")

                # WICHTIG: Beschreibung bleibt die ORIGINALE – kein Anhäufen von Hints!
                # Nur der 'reason' bekommt den neuen Hint.
                retry_step = PlanStep(
                    index       = step.index,
                    description = step.description.split(" – ")[0].replace("[Retry] ", ""),  # Original
                    skill       = step.skill,
                    params      = step.params,
                    reason      = hint or step.reason,
                )
                self.session.plan[current_step_idx] = retry_step
                self.session.status = LoopStatus.EXECUTING

            elif next_action == "replan":
                replan_count += 1
                step_retry_count = 0
                if replan_count > 2:
                    self._log("   ❌ Zu viele Replanning-Versuche – breche ab.")
                    self.session.status = LoopStatus.GOAL_FAILED
                    break
                self._log(f"   🔄 Replan #{replan_count}...")
                self.session.status = LoopStatus.PLANNING
                new_plan = self._create_plan(
                    goal,
                    context=f"Bisherige Versuche sind gescheitert: {reason}"
                )
                if new_plan:
                    self.session.plan = new_plan
                    current_step_idx = 0
                    self.session.status = LoopStatus.EXECUTING
                else:
                    self.session.status = LoopStatus.GOAL_FAILED
                    break

            elif next_action == "abort":
                self._log(f"   🛑 Abbruch: {reason}")
                self.session.status = LoopStatus.GOAL_FAILED
                break

            else:
                # Unbekannte Aktion → weiter
                step.status = StepStatus.DONE
                current_step_idx += 1

        # Phase 4: Zusammenfassung
        self.session.final_summary = self._create_summary()
        self._log("\n" + "─" * 60)
        self._log(f"📝 Zusammenfassung:\n{self.session.final_summary}")

        return self.session

    def abort(self):
        """Bricht den laufenden Loop sicher ab."""
        self._abort_flag = True
        self._log("\n⛔ Abbruch angefordert...")

    def get_status_dict(self) -> Dict:
        """Gibt den aktuellen Status als JSON-serialisierbares Dict zurück."""
        if not self.session:
            return {"status": "idle", "goal": None}

        return {
            "status":     self.session.status.value,
            "goal":       self.session.goal,
            "iteration":  self.session.iteration,
            "max":        self.max_iterations,
            "steps_total": len(self.session.plan),
            "steps_done": sum(1 for s in self.session.plan if s.status == StepStatus.DONE),
            "summary":    self.session.final_summary,
            "history":    self.session.history,
        }

    # -----------------------------------------------------------------------
    # Interne Phasen
    # -----------------------------------------------------------------------

    def _create_plan(self, goal: str, context: str = "") -> Optional[List[PlanStep]]:
        """Phase 1: LLM erstellt einen strukturierten Plan."""
        # Policy: interaktive Skills aus der Planner-Liste entfernen
        policy = get_policy()
        skills_text = self.kernel.manager.get_system_prompt_addition()
        policy_hint = policy.get_blocked_skills_hint()
        system = PLANNER_SYSTEM_PROMPT.format(skills=skills_text) + "\n\n" + policy_hint

        user_content = f"Erstelle einen Plan für dieses Ziel: {goal}"
        if context:
            user_content += f"\n\nZusätzlicher Kontext: {context}"

        messages = [
            {"role": "system",  "content": system},
            {"role": "user",    "content": user_content},
        ]

        try:
            raw = self.kernel.provider.chat(messages, force_json=True)
            data = self._parse_json(raw)

            if not data or "plan" not in data:
                logger.error(f"Planner lieferte kein valides JSON: {raw[:200]}")
                return None

            steps = []
            for item in data["plan"]:
                steps.append(PlanStep(
                    index       = item.get("index", len(steps)),
                    description = item.get("description", ""),
                    skill       = item.get("skill"),
                    params      = item.get("params") or {},
                    reason      = item.get("reason", ""),
                ))
            return steps

        except Exception as e:
            logger.error(f"Planner Fehler: {e}")
            return None

    def _execute_step(self, step: PlanStep) -> str:
        """Phase 2: Führt einen einzelnen Plan-Schritt aus."""
        if not step.skill:
            # Kein Skill – LLM direkt antworten lassen
            return self._ask_llm_directly(step.description)

        # ── Skill-Policy-Prüfung ──────────────────────────────
        policy = get_policy()
        decision, reason = policy.check(step.skill, ExecutionMode.AUTONOMOUS)

        if decision == PolicyDecision.BLOCK:
            step.status = StepStatus.SKIPPED
            msg = f"[Policy] Skill '{step.skill}' blockiert: {reason}"
            self._log(f"   🛡️  {msg}")
            logger.warning(msg)
            return f"BLOCKIERT: {reason} – Bitte einen anderen Ansatz wählen."

        if decision == PolicyDecision.WARN:
            self._log(f"   ⚠️  Policy-Warnung: {reason}")

        # Skill über den SkillManager ausführen
        try:
            # Skills ggf. neu laden (z.B. nach skill_erstellen)
            if step.skill not in self.kernel.manager.loaded_tools:
                self.kernel.load_skills()

            result = self.kernel.manager.execute_skill(step.skill, step.params)

            # Wenn neuer Skill erstellt wurde → Skills neu laden
            if "SUCCESS_CREATED" in str(result):
                self._log("   ✨ Neuer Skill erstellt – lade Skills neu...")
                self.kernel.load_skills()

            step.status = StepStatus.DONE
            return str(result)

        except Exception as e:
            step.status = StepStatus.FAILED
            step.error  = str(e)
            logger.error(f"Skill-Ausführung fehlgeschlagen: {e}")
            return f"FEHLER: {e}"

    def _evaluate(self, goal: str, step: PlanStep, result: str) -> Dict:
        """Phase 3: LLM bewertet ob das Ziel erreicht wurde."""
        steps_summary = "\n".join(
            f"  Schritt {e['step']+1}: {e['description']} → {str(e['result'])[:100]}"
            for e in self.session.history
        )

        system = EVALUATOR_SYSTEM_PROMPT.format(
            goal=goal,
            steps_summary=steps_summary or "(noch keine abgeschlossenen Schritte)",
            last_result=str(result)[:3000],  # War 500 – zu kurz für Code-Ausgaben
        )

        messages = [
            {"role": "system", "content": system},
            {"role": "user",   "content": "Bewerte den aktuellen Fortschritt."},
        ]

        try:
            raw  = self.kernel.provider.chat(messages, force_json=True)
            data = self._parse_json(raw)
            return data if data else {"goal_reached": False, "next_action": "continue", "reason": "Evaluation fehlgeschlagen"}
        except Exception as e:
            logger.error(f"Evaluator Fehler: {e}")
            return {"goal_reached": False, "next_action": "continue", "reason": str(e)}

    def _create_summary(self) -> str:
        """Phase 4: Erstellt eine lesbare Zusammenfassung für den User."""
        if not self.session:
            return "Kein Lauf vorhanden."

        steps_summary = "\n".join(
            f"  {e['step']+1}. {e['description']} → {str(e['result'])[:150]}"
            for e in self.session.history
        )

        system = SUMMARY_SYSTEM_PROMPT.format(
            goal=self.session.goal,
            status=self.session.status.value,
            steps_summary=steps_summary or "(keine Schritte ausgeführt)",
        )

        messages = [
            {"role": "system", "content": system},
            {"role": "user",   "content": "Fasse das Ergebnis zusammen."},
        ]

        try:
            return self.kernel.provider.chat(messages, force_json=False)
        except Exception as e:
            logger.error(f"Summary Fehler: {e}")
            return f"Lauf beendet mit Status: {self.session.status.value}"

    def _ask_llm_directly(self, task: str) -> str:
        """Führt einen Schritt ohne Skill direkt über das LLM aus."""
        messages = [
            {"role": "system", "content": "Du bist Ilija. Führe diese Aufgabe aus und antworte mit dem Ergebnis."},
            {"role": "user",   "content": task},
        ]
        try:
            return self.kernel.provider.chat(messages, force_json=False)
        except Exception as e:
            return f"Direktes LLM fehlgeschlagen: {e}"

    # -----------------------------------------------------------------------
    # Hilfsmethoden
    # -----------------------------------------------------------------------

    def _parse_json(self, raw: str) -> Optional[Dict]:
        """Parst JSON aus LLM-Antwort, toleriert Markdown-Codeblöcke."""
        import re
        # Markdown-Codeblöcke entfernen
        cleaned = re.sub(r"```(?:json)?", "", raw).replace("```", "").strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            # Fallback: erstes {...} herausziehen
            match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except Exception:
                    pass
        logger.warning(f"JSON-Parse fehlgeschlagen: {raw[:200]}")
        return None

    def _log(self, msg: str):
        """Gibt Fortschritt aus wenn verbose=True."""
        if self.verbose:
            from kernel import C as Colors
            # Farbiges Prefix je nach Inhalt
            if "✅" in msg or "📝" in msg:
                print(f"{Colors.GREEN}{msg}{Colors.RESET}")
            elif "❌" in msg or "FEHLER" in msg or "🛑" in msg:
                print(f"{Colors.RED}{msg}{Colors.RESET}")
            elif "🎯" in msg or "📋" in msg:
                print(f"{Colors.CYAN}{msg}{Colors.RESET}")
            elif "▶️" in msg or "🔧" in msg:
                print(f"{Colors.YELLOW}{msg}{Colors.RESET}")
            elif "🧠" in msg or "🔄" in msg:
                print(f"{Colors.MAGENTA}{msg}{Colors.RESET}")
            else:
                print(msg)
        logger.info(msg.strip())
