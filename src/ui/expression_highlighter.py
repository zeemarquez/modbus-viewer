"""
Syntax highlighter for variable expressions.
"""

from PySide6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor
from PySide6.QtCore import QRegularExpression


class ExpressionHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for variable expressions."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Register pattern (R0, R1, R100, etc.)
        register_format = QTextCharFormat()
        register_format.setForeground(QColor('#1976d2'))  # Blue
        register_format.setFontWeight(600)
        self.register_pattern = QRegularExpression(r'\bR\d+\b')
        self.highlighting_rules = [
            (self.register_pattern, register_format)
        ]
        
        # Function pattern
        function_format = QTextCharFormat()
        function_format.setForeground(QColor('#7b1fa2'))  # Purple
        function_format.setFontWeight(500)
        functions = ['abs', 'min', 'max', 'sqrt', 'round', 'int', 'float', 
                    'pow', 'sin', 'cos', 'tan', 'log', 'log10', 'exp']
        for func in functions:
            pattern = QRegularExpression(rf'\b{func}\b')
            self.highlighting_rules.append((pattern, function_format))
        
        # Operator pattern
        operator_format = QTextCharFormat()
        operator_format.setForeground(QColor('#ef6c00'))  # Orange
        operator_format.setFontWeight(600)
        operators = [r'\+', r'-', r'\*', r'/', r'//', r'%', r'\*\*', r'=', r'<', r'>', r'<=', r'>=', r'==', r'!=']
        for op in operators:
            pattern = QRegularExpression(op)
            self.highlighting_rules.append((pattern, operator_format))
        
        # Number pattern
        number_format = QTextCharFormat()
        number_format.setForeground(QColor('#2e7d32'))  # Green
        number_pattern = QRegularExpression(r'\b\d+\.?\d*\b')
        self.highlighting_rules.append((number_pattern, number_format))
        
        # Parentheses
        paren_format = QTextCharFormat()
        paren_format.setForeground(QColor('#757575'))  # Gray
        paren_format.setFontWeight(600)
        paren_pattern = QRegularExpression(r'[()]')
        self.highlighting_rules.append((paren_pattern, paren_format))
    
    def highlightBlock(self, text: str) -> None:
        """Apply highlighting to a block of text."""
        for pattern, format in self.highlighting_rules:
            iterator = pattern.globalMatch(text)
            while iterator.hasNext():
                match = iterator.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), format)





