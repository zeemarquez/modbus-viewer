"""
Syntax highlighter for variable expressions.
Supports multi-device D<id>.R<addr> syntax.
"""

import re
from PySide6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont


class ExpressionHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for variable expressions with multi-device support."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Define highlighting rules
        self._rules = []
        
        # Register references - D<id>.R<addr> format (primary)
        register_format = QTextCharFormat()
        register_format.setForeground(QColor('#1976d2'))  # Blue
        register_format.setFontWeight(QFont.Weight.Bold)
        self._rules.append((re.compile(r'\bD\d+\.R\d+\b'), register_format))
        
        # Legacy register references - R<addr> format
        legacy_register_format = QTextCharFormat()
        legacy_register_format.setForeground(QColor('#0d47a1'))  # Darker blue
        legacy_register_format.setFontWeight(QFont.Weight.Bold)
        self._rules.append((re.compile(r'(?<!\.)(?<!D\d)\bR\d+\b'), legacy_register_format))
        
        # Numbers
        number_format = QTextCharFormat()
        number_format.setForeground(QColor('#388e3c'))  # Green
        self._rules.append((re.compile(r'\b\d+\.?\d*\b'), number_format))
        
        # Functions
        function_format = QTextCharFormat()
        function_format.setForeground(QColor('#7b1fa2'))  # Purple
        function_format.setFontWeight(QFont.Weight.Bold)
        functions = ['abs', 'min', 'max', 'sqrt', 'round', 'int', 'float', 'pow',
                     'sin', 'cos', 'tan', 'log', 'log10', 'exp']
        pattern = r'\b(' + '|'.join(functions) + r')\b'
        self._rules.append((re.compile(pattern), function_format))
        
        # Operators
        operator_format = QTextCharFormat()
        operator_format.setForeground(QColor('#c62828'))  # Red
        self._rules.append((re.compile(r'[\+\-\*\/\%\^\(\)]'), operator_format))
    
    def highlightBlock(self, text: str) -> None:
        """Apply highlighting to a block of text."""
        for pattern, fmt in self._rules:
            for match in pattern.finditer(text):
                start = match.start()
                length = match.end() - start
                self.setFormat(start, length, fmt)
