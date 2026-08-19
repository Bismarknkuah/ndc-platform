import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../auth/auth_provider.dart';
import 'direct_messages_provider.dart';

class ConversationScreen extends StatelessWidget {
  const ConversationScreen({super.key, required this.otherUserId, required this.otherUserName});

  final String otherUserId;
  final String otherUserName;

  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider(
      create: (_) => ConversationProvider()..load(otherUserId),
      child: _ConversationView(otherUserId: otherUserId, otherUserName: otherUserName),
    );
  }
}

class _ConversationView extends StatefulWidget {
  const _ConversationView({required this.otherUserId, required this.otherUserName});

  final String otherUserId;
  final String otherUserName;

  @override
  State<_ConversationView> createState() => _ConversationViewState();
}

class _ConversationViewState extends State<_ConversationView> {
  final _messageController = TextEditingController();

  @override
  void dispose() {
    _messageController.dispose();
    super.dispose();
  }

  Future<void> _send() async {
    final text = _messageController.text.trim();
    if (text.isEmpty) return;
    _messageController.clear();
    await context.read<ConversationProvider>().send(widget.otherUserId, text);
  }

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<ConversationProvider>();
    final currentUserId = context.read<AuthProvider>().currentUser?.id;
    final timeFormat = DateFormat('h:mm a');

    return Scaffold(
      appBar: AppBar(title: Text(widget.otherUserName)),
      body: Column(
        children: [
          Expanded(
            child: Builder(
              builder: (context) {
                if (provider.isLoading && provider.messages.isEmpty) {
                  return const Center(child: CircularProgressIndicator());
                }
                if (provider.messages.isEmpty) {
                  return const Center(child: Text('No messages yet.'));
                }
                final ordered = provider.messages.reversed.toList();
                return ListView.builder(
                  padding: const EdgeInsets.all(12),
                  itemCount: ordered.length,
                  itemBuilder: (context, index) {
                    final message = ordered[index];
                    final isMine = message.senderId == currentUserId;
                    return Align(
                      alignment: isMine ? Alignment.centerRight : Alignment.centerLeft,
                      child: Container(
                        margin: const EdgeInsets.symmetric(vertical: 4),
                        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                        constraints: BoxConstraints(
                          maxWidth: MediaQuery.of(context).size.width * 0.75,
                        ),
                        decoration: BoxDecoration(
                          color: isMine
                              ? Theme.of(context).colorScheme.primaryContainer
                              : Theme.of(context).colorScheme.surfaceContainerHighest,
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Text(message.body),
                            const SizedBox(height: 2),
                            Text(
                              timeFormat.format(message.createdAt),
                              style: Theme.of(context).textTheme.bodySmall,
                            ),
                          ],
                        ),
                      ),
                    );
                  },
                );
              },
            ),
          ),
          SafeArea(
            child: Padding(
              padding: const EdgeInsets.all(8),
              child: Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: _messageController,
                      decoration: const InputDecoration(
                        hintText: 'Type a message...',
                        border: OutlineInputBorder(),
                        contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                      ),
                      onSubmitted: (_) => _send(),
                    ),
                  ),
                  const SizedBox(width: 8),
                  IconButton.filled(
                    onPressed: provider.isSending ? null : _send,
                    icon: const Icon(Icons.send),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
