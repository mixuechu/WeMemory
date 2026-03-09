#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Intelligent Person Merge Suggestions Generator
Analyzes person database and creates HTML file with smart merge suggestions
"""

import pickle
import json
import re
from collections import defaultdict
from typing import List, Dict, Set, Tuple
import html


class MergeSuggestion:
    """Represents a merge suggestion with reasoning"""

    def __init__(self, names: List[str], reason: str, priority: int,
                 conversations: Set[str], occurrences: Dict[str, int]):
        self.names = sorted(names)  # Canonical name should be first after sorting
        self.reason = reason
        self.priority = priority  # 1=highest, 5=lowest
        self.conversations = sorted(conversations)
        self.occurrences = occurrences  # name -> count
        self.total_occurrences = sum(occurrences.values())

    def to_dict(self):
        return {
            'names': self.names,
            'reason': self.reason,
            'priority': self.priority,
            'conversations': self.conversations,
            'occurrences': self.occurrences,
            'total_occurrences': self.total_occurrences
        }


class IntelligentMergeAnalyzer:
    """Analyzes person database and generates intelligent merge suggestions"""

    def __init__(self, person_db):
        self.persons = person_db['persons']
        self.person_index = person_db['person_index']
        self.conversation_persons = person_db['conversation_persons']
        self.suggestions = []

    def analyze(self):
        """Run all analysis methods"""
        print("Starting intelligent merge analysis...")

        # Group persons by name
        name_groups = defaultdict(list)
        for person in self.persons:
            name = person['name']
            name_groups[name].append(person)

        print(f"Total unique names: {len(name_groups)}")

        # 1. Analyze 米雪川 family members
        self._analyze_mixuechuan_family(name_groups)

        # 2. Analyze same conversation variants (妈/妈妈 in same conversation)
        self._analyze_same_conversation_variants(name_groups)

        # 3. Analyze obvious duplicates (任悦 vs 任悦律师)
        self._analyze_obvious_duplicates(name_groups)

        # 4. Analyze Unknown variants in same conversation
        self._analyze_unknown_variants(name_groups)

        # 5. Analyze professional title variants
        self._analyze_professional_titles(name_groups)

        # Sort by priority
        self.suggestions.sort(key=lambda s: (s.priority, -s.total_occurrences))

        print(f"Generated {len(self.suggestions)} merge suggestions")
        return self.suggestions

    def _analyze_mixuechuan_family(self, name_groups):
        """Analyze 米雪川 family member variants"""
        print("Analyzing 米雪川 family members...")

        # Find all 米雪川 related names
        mixuechuan_names = [name for name in name_groups.keys() if '米雪川' in name]

        # Group by relationship type
        mother_variants = []
        father_variants = []

        mother_patterns = ['妈', '母亲', 'mother']
        father_patterns = ['爸', '父亲', 'father']

        for name in mixuechuan_names:
            name_lower = name.lower()
            if any(p in name_lower for p in mother_patterns):
                mother_variants.append(name)
            elif any(p in name_lower for p in father_patterns):
                father_variants.append(name)

        # Create suggestions for mother variants
        if len(mother_variants) > 1:
            self._create_family_suggestion(mother_variants, '米雪川', '妈妈', name_groups)

        # Create suggestions for father variants
        if len(father_variants) > 1:
            self._create_family_suggestion(father_variants, '米雪川', '爸爸', name_groups)

    def _create_family_suggestion(self, variants, person_name, relation, name_groups):
        """Create a merge suggestion for family member variants"""
        if len(variants) <= 1:
            return

        conversations = set()
        occurrences = {}

        for variant in variants:
            for person in name_groups[variant]:
                conversations.add(person['conversation'])
            occurrences[variant] = len(name_groups[variant])

        reason = f"这些都是{person_name}的{relation}的不同称呼方式。在中文对话中，'的{relation}'、'{relation}'、'的{relation}{relation}'等都指代同一个人。"

        suggestion = MergeSuggestion(
            names=variants,
            reason=reason,
            priority=1,  # High priority - family relationships are clear
            conversations=conversations,
            occurrences=occurrences
        )
        self.suggestions.append(suggestion)

    def _analyze_same_conversation_variants(self, name_groups):
        """Analyze variants within the same conversation"""
        print("Analyzing same conversation variants...")

        # Group by conversation - optimized
        conv_names = defaultdict(set)
        for person in self.persons:
            conv_names[person['conversation']].add(person['name'])

        # Limit to conversations with reasonable number of people
        print(f"Total conversations: {len(conv_names)}")
        processed = 0

        # Find similar names in same conversation
        for conv, names in conv_names.items():
            names_list = list(names)
            # Skip conversations with too many people to avoid O(n^2) issues
            if len(names_list) > 50:
                continue

            processed += 1
            if processed % 100 == 0:
                print(f"  Processed {processed} conversations...")

            for i in range(len(names_list)):
                for j in range(i + 1, len(names_list)):
                    name1, name2 = names_list[i], names_list[j]
                    if self._are_relationship_variants(name1, name2):
                        # Create suggestion
                        conversations = {conv}
                        occurrences = {
                            name1: len([p for p in name_groups[name1] if p['conversation'] == conv]),
                            name2: len([p for p in name_groups[name2] if p['conversation'] == conv])
                        }

                        reason = f"在对话'{conv}'中，这两个称呼指代同一关系的不同表达形式（如'妈'和'妈妈'，'爸'和'爸爸'）。"

                        # Check if already suggested
                        if not self._already_suggested([name1, name2]):
                            suggestion = MergeSuggestion(
                                names=[name1, name2],
                                reason=reason,
                                priority=2,
                                conversations=conversations,
                                occurrences=occurrences
                            )
                            self.suggestions.append(suggestion)

    def _are_relationship_variants(self, name1, name2):
        """Check if two names are variants of same relationship"""
        # Common relationship variants
        variants = [
            (['妈', '妈妈', '母亲', 'mom', 'mother'], '母亲'),
            (['爸', '爸爸', '父亲', 'dad', 'father'], '父亲'),
            (['姐', '姐姐', 'sister'], '姐姐'),
            (['哥', '哥哥', 'brother'], '哥哥'),
            (['弟', '弟弟'], '弟弟'),
            (['妹', '妹妹'], '妹妹'),
        ]

        name1_lower = name1.lower()
        name2_lower = name2.lower()

        for variant_list, _ in variants:
            matches = []
            for v in variant_list:
                if v in name1_lower:
                    matches.append(name1)
                if v in name2_lower:
                    matches.append(name2)

            if len(set(matches)) == 2:  # Both names match this variant group
                # But not if one is possessive of the other
                if name1 in name2 or name2 in name1:
                    continue
                return True

        return False

    def _analyze_obvious_duplicates(self, name_groups):
        """Analyze obvious duplicates like 任悦 vs 任悦律师"""
        print("Analyzing obvious duplicates...")

        all_names = list(name_groups.keys())
        print(f"Total unique names: {len(all_names)}")

        # Optimize by creating a lookup dict
        name_prefixes = defaultdict(list)
        for name in all_names:
            if len(name) >= 2:
                # Index by first 2-3 characters
                for prefix_len in [2, 3]:
                    if len(name) >= prefix_len:
                        prefix = name[:prefix_len]
                        name_prefixes[prefix].append(name)

        # Only compare names with same prefix
        checked_pairs = set()
        for prefix, names in name_prefixes.items():
            if len(names) < 2:
                continue

            for i in range(len(names)):
                for j in range(i + 1, len(names)):
                    name1, name2 = names[i], names[j]
                    pair = tuple(sorted([name1, name2]))

                    if pair in checked_pairs:
                        continue
                    checked_pairs.add(pair)

                    # Skip if already suggested
                    if self._already_suggested([name1, name2]):
                        continue

                    # Check if one is substring of another with professional title
                    if self._is_professional_variant(name1, name2):
                        conversations = set()
                        for person in name_groups[name1]:
                            conversations.add(person['conversation'])
                        for person in name_groups[name2]:
                            conversations.add(person['conversation'])

                        occurrences = {
                            name1: len(name_groups[name1]),
                            name2: len(name_groups[name2])
                        }

                        reason = f"一个名字是另一个名字加上职业头衔或称呼（如'{min(name1, name2, key=len)}'和'{max(name1, name2, key=len)}'），很可能是同一个人。"

                        suggestion = MergeSuggestion(
                            names=[name1, name2],
                            reason=reason,
                            priority=2,
                            conversations=conversations,
                            occurrences=occurrences
                        )
                        self.suggestions.append(suggestion)

        print(f"  Found {len(self.suggestions)} duplicate suggestions so far")

    def _is_professional_variant(self, name1, name2):
        """Check if names are professional variants"""
        short_name = min(name1, name2, key=len)
        long_name = max(name1, name2, key=len)

        if len(short_name) < 2:
            return False

        # Check if short name is in long name
        if short_name not in long_name:
            return False

        # Professional titles
        titles = ['律师', '医生', '老师', '教授', '博士', '总', '经理',
                  '主任', '院长', '校长', '姐', '哥', '小', '老']

        # Check if difference is a title
        diff = long_name.replace(short_name, '')
        return any(title in diff for title in titles)

    def _analyze_unknown_variants(self, name_groups):
        """Analyze Unknown person variants in same conversation"""
        print("Analyzing Unknown variants...")

        # Find all unknown names
        unknown_names = [name for name in name_groups.keys()
                        if 'unknown' in name.lower() or 'unnamed' in name.lower() or
                        'unidentified' in name.lower() or name.startswith('Unknown_')]

        print(f"  Found {len(unknown_names)} unknown name variants")

        # Group by conversation - limit to avoid memory issues
        conv_unknowns = defaultdict(set)
        for name in unknown_names:
            for person in name_groups[name]:
                conv_unknowns[person['conversation']].add(name)

        # Create suggestions for unknowns in same conversation (limit to first 100 conversations)
        count = 0
        for conv, names in list(conv_unknowns.items())[:100]:
            unique_names = list(names)
            if len(unique_names) > 1 and len(unique_names) <= 5:  # Reasonable number to merge
                # Only suggest if they seem related
                conversations = {conv}
                occurrences = {}
                for name in unique_names:
                    occurrences[name] = len([p for p in name_groups[name]
                                            if p['conversation'] == conv])

                reason = f"在对话'{conv}'中，这些都是未知人物的不同表达方式，应该合并为一个人。"

                if not self._already_suggested(unique_names):
                    suggestion = MergeSuggestion(
                        names=unique_names,
                        reason=reason,
                        priority=3,
                        conversations=conversations,
                        occurrences=occurrences
                    )
                    self.suggestions.append(suggestion)
                    count += 1

        print(f"  Created {count} unknown variant suggestions")

    def _analyze_professional_titles(self, name_groups):
        """Analyze names with different professional titles"""
        print("Analyzing professional title variants...")

        # This is already covered by _analyze_obvious_duplicates
        # Skip to avoid duplication
        print("  Skipping (covered by obvious duplicates analysis)")

    def _already_suggested(self, names):
        """Check if these names were already suggested"""
        names_set = set(names)
        for suggestion in self.suggestions:
            if set(suggestion.names) == names_set:
                return True
        return False


def generate_html(suggestions: List[MergeSuggestion], output_file: str):
    """Generate HTML file with merge suggestions"""

    html_template = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>智能人物合并建议</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Microsoft YaHei", sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }

        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }

        .header h1 {
            font-size: 32px;
            margin-bottom: 10px;
        }

        .header p {
            font-size: 16px;
            opacity: 0.9;
        }

        .stats {
            display: flex;
            justify-content: space-around;
            padding: 20px;
            background: #f8f9fa;
            border-bottom: 2px solid #e9ecef;
        }

        .stat-item {
            text-align: center;
        }

        .stat-number {
            font-size: 32px;
            font-weight: bold;
            color: #667eea;
        }

        .stat-label {
            font-size: 14px;
            color: #6c757d;
            margin-top: 5px;
        }

        .controls {
            padding: 20px;
            background: #fff;
            border-bottom: 2px solid #e9ecef;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .filter-group {
            display: flex;
            gap: 10px;
            align-items: center;
        }

        .filter-btn {
            padding: 8px 16px;
            border: 2px solid #667eea;
            background: white;
            color: #667eea;
            border-radius: 20px;
            cursor: pointer;
            font-size: 14px;
            transition: all 0.3s;
        }

        .filter-btn.active {
            background: #667eea;
            color: white;
        }

        .filter-btn:hover {
            background: #667eea;
            color: white;
        }

        .save-btn {
            padding: 10px 24px;
            background: #28a745;
            color: white;
            border: none;
            border-radius: 25px;
            cursor: pointer;
            font-size: 16px;
            font-weight: bold;
            transition: all 0.3s;
        }

        .save-btn:hover {
            background: #218838;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(40, 167, 69, 0.4);
        }

        .suggestions {
            padding: 20px;
            max-height: calc(100vh - 400px);
            overflow-y: auto;
        }

        .suggestion-card {
            background: white;
            border: 2px solid #e9ecef;
            border-radius: 15px;
            padding: 20px;
            margin-bottom: 20px;
            transition: all 0.3s;
        }

        .suggestion-card:hover {
            box-shadow: 0 8px 24px rgba(0,0,0,0.1);
            transform: translateY(-2px);
        }

        .suggestion-card.approved {
            border-color: #28a745;
            background: #f1f9f3;
        }

        .suggestion-card.rejected {
            border-color: #dc3545;
            background: #fef2f2;
            opacity: 0.6;
        }

        .priority-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: bold;
            margin-bottom: 10px;
        }

        .priority-1 {
            background: #dc3545;
            color: white;
        }

        .priority-2 {
            background: #fd7e14;
            color: white;
        }

        .priority-3 {
            background: #ffc107;
            color: #000;
        }

        .priority-4 {
            background: #17a2b8;
            color: white;
        }

        .priority-5 {
            background: #6c757d;
            color: white;
        }

        .names-section {
            margin: 15px 0;
        }

        .name-tag {
            display: inline-block;
            background: #667eea;
            color: white;
            padding: 6px 14px;
            border-radius: 20px;
            margin: 5px;
            font-size: 14px;
        }

        .name-tag .count {
            background: rgba(255,255,255,0.3);
            padding: 2px 8px;
            border-radius: 10px;
            margin-left: 8px;
            font-size: 12px;
        }

        .reason {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 10px;
            margin: 15px 0;
            font-size: 14px;
            line-height: 1.6;
            color: #495057;
        }

        .conversations {
            margin: 15px 0;
        }

        .conversations-title {
            font-size: 14px;
            color: #6c757d;
            margin-bottom: 8px;
        }

        .conversation-tag {
            display: inline-block;
            background: #e9ecef;
            color: #495057;
            padding: 4px 10px;
            border-radius: 12px;
            margin: 3px;
            font-size: 12px;
        }

        .actions {
            display: flex;
            gap: 10px;
            margin-top: 15px;
        }

        .approve-btn, .reject-btn {
            flex: 1;
            padding: 10px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            font-weight: bold;
            transition: all 0.3s;
        }

        .approve-btn {
            background: #28a745;
            color: white;
        }

        .approve-btn:hover {
            background: #218838;
        }

        .reject-btn {
            background: #dc3545;
            color: white;
        }

        .reject-btn:hover {
            background: #c82333;
        }

        .suggestion-card.approved .approve-btn,
        .suggestion-card.rejected .reject-btn {
            opacity: 0.5;
            cursor: default;
        }

        .total-occurrences {
            font-size: 14px;
            color: #6c757d;
            margin-top: 10px;
        }

        ::-webkit-scrollbar {
            width: 10px;
        }

        ::-webkit-scrollbar-track {
            background: #f1f1f1;
        }

        ::-webkit-scrollbar-thumb {
            background: #667eea;
            border-radius: 5px;
        }

        ::-webkit-scrollbar-thumb:hover {
            background: #764ba2;
        }

        .empty-state {
            text-align: center;
            padding: 60px 20px;
            color: #6c757d;
        }

        .empty-state-icon {
            font-size: 64px;
            margin-bottom: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 智能人物合并建议</h1>
            <p>基于对话上下文和语义分析的智能合并建议</p>
        </div>

        <div class="stats">
            <div class="stat-item">
                <div class="stat-number" id="total-suggestions">0</div>
                <div class="stat-label">总建议数</div>
            </div>
            <div class="stat-item">
                <div class="stat-number" id="approved-count">0</div>
                <div class="stat-label">已批准</div>
            </div>
            <div class="stat-item">
                <div class="stat-number" id="rejected-count">0</div>
                <div class="stat-label">已拒绝</div>
            </div>
            <div class="stat-item">
                <div class="stat-number" id="pending-count">0</div>
                <div class="stat-label">待处理</div>
            </div>
        </div>

        <div class="controls">
            <div class="filter-group">
                <span>筛选：</span>
                <button class="filter-btn active" onclick="filterSuggestions('all')">全部</button>
                <button class="filter-btn" onclick="filterSuggestions('pending')">待处理</button>
                <button class="filter-btn" onclick="filterSuggestions('approved')">已批准</button>
                <button class="filter-btn" onclick="filterSuggestions('rejected')">已拒绝</button>
            </div>
            <button class="save-btn" onclick="saveDecisions()">💾 保存决定</button>
        </div>

        <div class="suggestions" id="suggestions-container">
            <!-- Suggestions will be inserted here -->
        </div>
    </div>

    <script>
        // Load suggestions data
        const suggestions = SUGGESTIONS_DATA;

        // Track decisions
        const decisions = {};

        // Initialize
        function init() {
            renderSuggestions();
            updateStats();
        }

        // Render suggestions
        function renderSuggestions() {
            const container = document.getElementById('suggestions-container');

            if (suggestions.length === 0) {
                container.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-state-icon">📭</div>
                        <h2>暂无合并建议</h2>
                        <p>系统未发现需要合并的人物</p>
                    </div>
                `;
                return;
            }

            container.innerHTML = suggestions.map((suggestion, index) => {
                const status = decisions[index] || 'pending';
                const priorityLabels = {
                    1: '最高优先级',
                    2: '高优先级',
                    3: '中优先级',
                    4: '低优先级',
                    5: '最低优先级'
                };

                return `
                    <div class="suggestion-card ${status}" data-index="${index}" data-status="${status}">
                        <span class="priority-badge priority-${suggestion.priority}">
                            ${priorityLabels[suggestion.priority]}
                        </span>

                        <div class="names-section">
                            <strong>建议合并：</strong>
                            ${suggestion.names.map(name => `
                                <span class="name-tag">
                                    ${escapeHtml(name)}
                                    <span class="count">${suggestion.occurrences[name]}次</span>
                                </span>
                            `).join('')}
                        </div>

                        <div class="reason">
                            <strong>🧠 原因：</strong>${escapeHtml(suggestion.reason)}
                        </div>

                        <div class="conversations">
                            <div class="conversations-title">📍 出现在对话：</div>
                            ${suggestion.conversations.slice(0, 10).map(conv => `
                                <span class="conversation-tag">${escapeHtml(conv)}</span>
                            `).join('')}
                            ${suggestion.conversations.length > 10 ?
                                `<span class="conversation-tag">... 还有 ${suggestion.conversations.length - 10} 个对话</span>`
                                : ''}
                        </div>

                        <div class="total-occurrences">
                            总出现次数: <strong>${suggestion.total_occurrences}</strong>
                        </div>

                        <div class="actions">
                            <button class="approve-btn" onclick="approveSuggestion(${index})">
                                ✓ 批准合并
                            </button>
                            <button class="reject-btn" onclick="rejectSuggestion(${index})">
                                ✗ 拒绝合并
                            </button>
                        </div>
                    </div>
                `;
            }).join('');
        }

        // Approve suggestion
        function approveSuggestion(index) {
            const card = document.querySelector(`[data-index="${index}"]`);
            if (card.classList.contains('approved')) return;

            decisions[index] = 'approved';
            card.classList.remove('rejected', 'pending');
            card.classList.add('approved');
            card.dataset.status = 'approved';
            updateStats();
        }

        // Reject suggestion
        function rejectSuggestion(index) {
            const card = document.querySelector(`[data-index="${index}"]`);
            if (card.classList.contains('rejected')) return;

            decisions[index] = 'rejected';
            card.classList.remove('approved', 'pending');
            card.classList.add('rejected');
            card.dataset.status = 'rejected';
            updateStats();
        }

        // Filter suggestions
        function filterSuggestions(filter) {
            // Update active button
            document.querySelectorAll('.filter-btn').forEach(btn => {
                btn.classList.remove('active');
            });
            event.target.classList.add('active');

            // Filter cards
            const cards = document.querySelectorAll('.suggestion-card');
            cards.forEach(card => {
                if (filter === 'all') {
                    card.style.display = 'block';
                } else {
                    const status = decisions[card.dataset.index] || 'pending';
                    card.style.display = status === filter ? 'block' : 'none';
                }
            });
        }

        // Update statistics
        function updateStats() {
            const total = suggestions.length;
            const approved = Object.values(decisions).filter(d => d === 'approved').length;
            const rejected = Object.values(decisions).filter(d => d === 'rejected').length;
            const pending = total - approved - rejected;

            document.getElementById('total-suggestions').textContent = total;
            document.getElementById('approved-count').textContent = approved;
            document.getElementById('rejected-count').textContent = rejected;
            document.getElementById('pending-count').textContent = pending;
        }

        // Save decisions
        function saveDecisions() {
            const result = {
                timestamp: new Date().toISOString(),
                total_suggestions: suggestions.length,
                decisions: {},
                approved_merges: [],
                rejected_merges: []
            };

            suggestions.forEach((suggestion, index) => {
                const decision = decisions[index] || 'pending';
                result.decisions[index] = {
                    names: suggestion.names,
                    decision: decision,
                    reason: suggestion.reason,
                    priority: suggestion.priority
                };

                if (decision === 'approved') {
                    result.approved_merges.push({
                        names: suggestion.names,
                        canonical_name: suggestion.names[0],  // First name as canonical
                        reason: suggestion.reason
                    });
                } else if (decision === 'rejected') {
                    result.rejected_merges.push({
                        names: suggestion.names,
                        reason: suggestion.reason
                    });
                }
            });

            // Download as JSON
            const blob = new Blob([JSON.stringify(result, null, 2)], {type: 'application/json'});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'merge_decisions.json';
            a.click();
            URL.revokeObjectURL(url);

            alert(`已保存！\\n批准: ${result.approved_merges.length}\\n拒绝: ${result.rejected_merges.length}\\n待处理: ${suggestions.length - result.approved_merges.length - result.rejected_merges.length}`);
        }

        // HTML escape
        function escapeHtml(text) {
            const map = {
                '&': '&amp;',
                '<': '&lt;',
                '>': '&gt;',
                '"': '&quot;',
                "'": '&#039;'
            };
            return text.replace(/[&<>"']/g, m => map[m]);
        }

        // Initialize on load
        init();
    </script>
</body>
</html>
"""

    # Convert suggestions to JSON
    suggestions_json = json.dumps([s.to_dict() for s in suggestions], ensure_ascii=False, indent=2)

    # Replace placeholder with actual data
    html_content = html_template.replace('SUGGESTIONS_DATA', suggestions_json)

    # Write file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"HTML file generated: {output_file}")


def main():
    print("Loading person database...")
    with open('person_database.pkl', 'rb') as f:
        person_db = pickle.load(f)

    print(f"Loaded {len(person_db['persons'])} person records")

    # Analyze
    analyzer = IntelligentMergeAnalyzer(person_db)
    suggestions = analyzer.analyze()

    # Generate HTML
    output_file = 'intelligent_merge_suggestions.html'
    generate_html(suggestions, output_file)

    print(f"\n✅ Generated {len(suggestions)} suggestions")
    print(f"📄 HTML file: {output_file}")
    print("\nPriority breakdown:")
    for priority in range(1, 6):
        count = len([s for s in suggestions if s.priority == priority])
        if count > 0:
            print(f"  Priority {priority}: {count} suggestions")


if __name__ == '__main__':
    main()
