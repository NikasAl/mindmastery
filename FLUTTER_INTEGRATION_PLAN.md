# План интеграции MindMastery Flutter с MindVector Server

## 📋 Обзор

**Цель**: Создать Android-приложение MindMastery на Flutter, использующее существующий сервер MindVector для LLM-запросов.

**Архитектура**:
```
┌─────────────────┐      API       ┌──────────────────┐
│  Flutter App    │ ◄──────────► │  MindVector API  │
│  (Android)      │               │  (FastAPI)       │
│                 │               │                  │
│  - Прогресс     │               │  - Problems ✓    │
│  - Кэш          │               │  - LLM Client ✓  │
│  - UI           │               │  - Skills (NEW)  │
└─────────────────┘               │  - Exercises(N)  │
                                  └──────────────────┘
```

---

## 🗄️ Часть 1: Изменения в БД MindVector

### Новые таблицы (миграция Alembic)

```python
# models.py - добавить

class SkillCategory(enum.Enum):
    computational = "computational"
    memory = "memory"
    visualization = "visualization"
    strategic = "strategic"
    mnemonic = "mnemonic"
    conceptual = "conceptual"


class DifficultyLevel(enum.Enum):
    intro = "intro"
    basic = "basic"
    intermediate = "intermediate"
    advanced = "advanced"
    mastery = "mastery"


class Skill(Base):
    """Навык для ментальных вычислений (из декомпозиции задачи)"""
    __tablename__ = "skills"

    id = Column(Integer, primary_key=True)
    problem_id = Column(Integer, ForeignKey("problems.id"), nullable=False, index=True)
    
    # Идентификация
    skill_id = Column(String(50), nullable=False)  # например, "vis_01"
    name = Column(String(200), nullable=False)
    description = Column(Text)
    
    # Классификация
    category = Column(SQLEnum(SkillCategory), default=SkillCategory.computational)
    difficulty_base = Column(Integer, default=5)  # 1-10
    cognitive_load = Column(Integer, default=5)   # 1-10
    
    # Зависимости
    prerequisites = Column(JSON, default=list)  # ["skill_id1", "skill_id2"]
    
    # Обучение
    tips = Column(JSON, default=list)
    mnemonics = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.now)
    
    # Связи
    problem = relationship("Problem", backref="skills")
    exercises = relationship("Exercise", back_populates="skill")
    
    __table_args__ = (
        Index('ix_skills_problem_skill', 'problem_id', 'skill_id', unique=True),
    )


class Exercise(Base):
    """Упражнение для тренировки навыка"""
    __tablename__ = "exercises"

    id = Column(Integer, primary_key=True)
    skill_id = Column(Integer, ForeignKey("skills.id"), nullable=False, index=True)
    
    # Идентификация
    exercise_id = Column(String(50), nullable=False)  # например, "ex_vis_01_01"
    
    # Уровень сложности
    level = Column(SQLEnum(DifficultyLevel), default=DifficultyLevel.intro)
    
    # Контент
    question = Column(Text, nullable=False)           # LaTeX
    question_plain = Column(Text, nullable=False)     # Plain text
    answer = Column(String(200), nullable=False)
    solution_steps = Column(JSON, default=list)
    hints = Column(JSON, default=list)
    
    # Метаданные
    time_estimate = Column(Integer, default=30)  # секунды
    cognitive_load = Column(Integer, default=5)
    
    # Верификация
    is_verified = Column(Boolean, default=False)
    verified_at = Column(DateTime, nullable=True)
    corrected_answer = Column(String(200), nullable=True)  # Если был исправлен
    
    created_at = Column(DateTime, default=datetime.now)
    
    # Связи
    skill = relationship("Skill", back_populates="exercises")
    
    __table_args__ = (
        Index('ix_exercises_skill_exercise', 'skill_id', 'exercise_id', unique=True),
    )


class TaskDecomposition(Base):
    """Результат декомпозиции задачи (кеширование)"""
    __tablename__ = "task_decompositions"

    id = Column(Integer, primary_key=True)
    problem_id = Column(Integer, ForeignKey("problems.id"), nullable=False, unique=True)
    
    # Решение
    full_solution = Column(JSON, default=list)  # ["Шаг 1", "Шаг 2", ...]
    skill_graph = Column(JSON, default=dict)    # {"order": [...], "skill_id": [...]}
    
    # Оценка
    estimated_time = Column(Integer, default=15)  # минуты
    
    created_at = Column(DateTime, default=datetime.now)
    
    # Связи
    problem = relationship("Problem", backref="decomposition")
```

### Миграция Alembic

```bash
cd /home/z/my-project/mindvector
alembic revision -m "add_mindmastery_tables"
```

---

## 🔌 Часть 2: Новые API Endpoints

### `/api/v1/mastery/` - новый роутер

```python
# app/api/v1/mastery.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.security import get_current_user_id

router = APIRouter(prefix="/mastery", tags=["MindMastery"])


@router.post("/decompose/{problem_id}")
async def decompose_problem(
    problem_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """
    Декомпозиция задачи на навыки.
    
    - Использует существующий LLM клиент
    - Кеширует результат в БД
    - Возвращает список навыков с упражнениями
    """
    pass


@router.post("/exercises/generate/{skill_id}")
async def generate_exercises(
    skill_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """
    Ленивая генерация упражнений для навыка.
    
    - Генерирует только когда запрошено
    - Кеширует в БД
    - Возвращает упражнения по уровням
    """
    pass


@router.post("/exercises/verify/{exercise_id}")
async def verify_exercise(
    exercise_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """
    Верификация упражнения через LLM.
    
    - Проверяет корректность ответа и решения
    - Автоматически исправляет в БД при ошибке
    """
    pass


@router.get("/problems/{problem_id}/skills")
async def get_problem_skills(
    problem_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """Получить навыки задачи (с кэшированием)"""
    pass


@router.get("/skills/{skill_id}/exercises")
async def get_skill_exercises(
    skill_id: int,
    level: Optional[str] = None,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """Получить упражнения для навыка"""
    pass
```

### Регистрация в router.py

```python
# app/api/v1/router.py
from app.api.v1 import mastery

api_router.include_router(mastery.router)
```

---

## 📱 Часть 3: Flutter App

### Структура проекта

```
lib/
├── main.dart
├── app/
│   ├── app.dart
│   └── routes.dart
├── data/
│   ├── models/
│   │   ├── problem.dart
│   │   ├── skill.dart
│   │   ├── exercise.dart
│   │   └── user_progress.dart
│   ├── repositories/
│   │   ├── problem_repository.dart
│   │   └── progress_repository.dart
│   └── services/
│       ├── api_client.dart
│       └── local_storage.dart
├── domain/
│   ├── usecases/
│   │   ├── decompose_problem.dart
│   │   ├── practice_skill.dart
│   │   └── verify_exercise.dart
│   └── entities/
│       └── ... 
└── ui/
    ├── screens/
    │   ├── home/
    │   ├── problem_list/
    │   ├── skill_roadmap/
    │   └── practice/
    └── widgets/
        ├── skill_card.dart
        ├── exercise_card.dart
        └── progress_indicator.dart
```

### Хранение прогресса (локально)

```dart
// data/services/local_storage.dart
import 'package:shared_preferences/shared_preferences.dart';
import 'dart:convert';

class LocalProgressStorage {
  final SharedPreferences _prefs;
  
  static const String _keyPrefix = 'mastery_progress_';
  
  Future<void> saveProgress(String taskId, String skillId, SkillProgress progress) async {
    final key = '$_keyPrefix${taskId}_$skillId';
    await _prefs.setString(key, jsonEncode(progress.toJson()));
  }
  
  Future<SkillProgress?> getProgress(String taskId, String skillId) async {
    final key = '$_keyPrefix${taskId}_$skillId';
    final data = _prefs.getString(key);
    if (data == null) return null;
    return SkillProgress.fromJson(jsonDecode(data));
  }
  
  Future<Map<String, SkillProgress>> getAllProgress(String taskId) async {
    final keys = _prefs.getKeys()
        .where((k) => k.startsWith('$_keyPrefix$taskId'));
    
    final result = <String, SkillProgress>{};
    for (final key in keys) {
      final skillId = key.replaceFirst('$_keyPrefix${taskId}_', '');
      final data = _prefs.getString(key);
      if (data != null) {
        result[skillId] = SkillProgress.fromJson(jsonDecode(data));
      }
    }
    return result;
  }
}

class SkillProgress {
  final int exercisesCompleted;
  final int exercisesCorrect;
  final double masteryScore;
  final int streak;
  final DateTime lastPracticed;
  
  // JSON serialization...
}
```

### API Client

```dart
// data/services/api_client.dart
import 'package:dio/dio.dart';

class MindVectorApiClient {
  final Dio _dio;
  final String baseUrl;
  
  MindVectorApiClient({
    required this.baseUrl,
    required String authToken,
  }) : _dio = Dio(BaseOptions(
    baseUrl: baseUrl,
    headers: {'Authorization': 'Bearer $authToken'},
  ));
  
  // Problems
  Future<List<Problem>> getProblems({String? source, String? tag});
  Future<Problem> getProblem(int id);
  
  // MindMastery
  Future<DecompositionResult> decomposeProblem(int problemId);
  Future<List<Exercise>> generateExercises(int skillId);
  Future<VerificationResult> verifyExercise(int exerciseId);
  Future<List<Skill>> getProblemSkills(int problemId);
  Future<List<Exercise>> getSkillExercises(int skillId, {String? level});
}
```

---

## 🔄 Часть 4: Переиспользование LLM Infrastructure

### Промпты MindMastery → MindVector

```python
# app/services/mastery_prompts.py

DECOMPOSITION_SYSTEM_PROMPT = """Ты — эксперт по когнитивной психологии и ментальным вычислениям..."""

DECOMPOSITION_PROMPT = """Декомпозируй следующую задачу на навыки..."""

EXERCISE_GENERATION_PROMPT = """Сгенерируй упражнения для тренировки навыка..."""

EXERCISE_VERIFICATION_PROMPT = """Ты — строгий проверяющий математических решений..."""
```

### Использование существующего LLM клиента

```python
# app/services/mastery_service.py

from app.services.llm_client import call_openrouter_chat
from app.services.mastery_prompts import (
    DECOMPOSITION_SYSTEM_PROMPT,
    EXERCISE_GENERATION_PROMPT,
    EXERCISE_VERIFICATION_PROMPT
)

async def decompose_task(task_text: str, task_type: str) -> dict:
    """Декомпозиция через существующий LLM клиент"""
    messages = [
        {"role": "system", "content": DECOMPOSITION_SYSTEM_PROMPT},
        {"role": "user", "content": f"Задача ({task_type}): {task_text}"}
    ]
    
    response = await call_openrouter_chat(
        messages,
        model="google/gemini-2.0-flash-lite-001"  # Дешёвая модель
    )
    
    return parse_json_response(response)


async def generate_skill_exercises(skill: dict, context: str) -> dict:
    """Генерация упражнений для навыка"""
    messages = [
        {"role": "system", "content": EXERCISE_GENERATION_PROMPT.format(
            skill=skill,
            context=context,
            skill_id=skill['id']
        )}
    ]
    
    response = await call_openrouter_chat(
        messages,
        model="google/gemini-2.0-flash-lite-001"
    )
    
    return parse_json_response(response)
```

---

## 📊 Часть 5: Схема данных Flutter ↔ Server

### Request/Response Flow

```
1. Flutter: GET /api/v1/problems → List<Problem>
   
2. Flutter: POST /api/v1/mastery/decompose/{problem_id}
   Server: 
   - Check cache (TaskDecomposition table)
   - If not cached → LLM decompose → Save skills + cache
   Response: DecompositionResult {
       skills: [Skill],
       full_solution: [String],
       estimated_time: int
   }

3. Flutter: POST /api/v1/mastery/exercises/generate/{skill_id}
   Server:
   - Check cache (Exercise table)
   - If not cached → LLM generate → Save exercises
   Response: ExercisesByLevel {
       intro: [Exercise],
       basic: [Exercise],
       ...
   }

4. Flutter: Локально сохраняет прогресс тренировки

5. Flutter (optional): POST /api/v1/mastery/exercises/verify/{exercise_id}
   Server:
   - LLM verification
   - Update exercise if error found
   Response: VerificationResult
```

---

## 🚀 Часть 6: Этапы разработки

### Этап 1: Server-side (1-2 дня)
- [ ] Миграция БД (skills, exercises, task_decompositions)
- [ ] API endpoints `/mastery/*`
- [ ] Переиспользование LLM клиента
- [ ] Кэширование декомпозиций

### Этап 2: Flutter Core (3-4 дня)
- [ ] Проект Flutter (Clean Architecture)
- [ ] API client + auth
- [ ] Models (Problem, Skill, Exercise, Progress)
- [ ] Local storage (SharedPreferences/Hive)

### Этап 3: Flutter UI (3-4 дня)
- [ ] Экран списка задач
- [ ] Экран декомпозиции (роадмап навыков)
- [ ] Экран практики упражнения
- [ ] Экран статистики/прогресса

### Этап 4: Polish (1-2 дня)
- [ ] Анимации, feedback
- [ ] Оффлайн-режим (кэш)
- [ ] LaTeX рендеринг

---

## 🔧 Конфигурация

### MindVector settings

```python
# app.conf
# Добавить модели для MindMastery
MASTERY_DECOMPOSITION_MODEL=google/gemini-2.0-flash-lite-001
MASTERY_EXERCISE_MODEL=google/gemini-2.0-flash-lite-001
MASTERY_VERIFICATION_MODEL=google/gemini-2.5-flash
```

### Flutter config

```dart
// lib/app/config/app_config.dart
class AppConfig {
  static String apiBaseUrl = 'https://mindvector.example.com/api/v1';
  static String defaultModel = 'gemini-2.0-flash-lite-001';
}
```

---

## ⚡ Оптимизации

1. **Кэширование декомпозиций** - один раз на задачу
2. **Ленивая генерация упражнений** - только по требованию
3. **Локальный прогресс** - минимальная нагрузка на сервер
4. **Batch запросы** - получить все навыки за раз
5. **Верификация опционально** - только при подозрении на ошибку

---

## 🔐 Аутентификация

Использовать существующую JWT систему MindVector:

```dart
// Flutter
final token = await authService.login(email, password);
apiClient.setAuthToken(token);

// Или анонимная аутентификация
final token = await authService.anonymousLogin(deviceId);
```

---

## 📦 Зависимости Flutter

```yaml
# pubspec.yaml
dependencies:
  flutter:
    sdk: flutter
  
  # State management
  flutter_riverpod: ^2.4.0
  
  # Networking
  dio: ^5.4.0
  
  # Local storage
  shared_preferences: ^2.2.0
  hive: ^2.2.0
  hive_flutter: ^1.1.0
  
  # LaTeX rendering
  flutter_math_fork: ^0.7.0
  flutter_tex: ^4.0.0  # Alternative
  
  # UI
  flutter_animate: ^4.3.0
  go_router: ^13.0.0
  
  # Utils
  freezed_annotation: ^2.4.0
  json_annotation: ^4.8.0
```

---

## 🎯 MVP Scope

**Включить в MVP:**
- Просмотр задач из MindVector
- Декомпозиция с кэшированием
- Генерация упражнений (лениво)
- Практика с проверкой ответов
- Локальный прогресс

**Отложить до v2:**
- Синхронизация прогресса с сервером
- Мультиплеер/рейтинг
- Кастомные задачи пользователя
- Темная тема
