"""
Chatbot服务模块
包含各种服务类的实现
"""

from .question_rewrite import QuestionRewriteService
from .security_audit import SecurityAuditService
from .intent_recognition import IntentRecognitionService
from .answer_generation import AnswerGenerationService
from .conversation_context import ConversationContextService
from .response_cache import ResponseCacheService

# AutoTitleService 延迟导入，因为它在模块级别实例化 ChatOpenAI（需要 API key）
def _get_auto_title_service_class():
    from .auto_title_service import AutoTitleService
    return AutoTitleService

__all__ = [
    'QuestionRewriteService',
    'SecurityAuditService',
    'IntentRecognitionService',
    'AnswerGenerationService',
    'ConversationContextService',
    'ResponseCacheService',
]