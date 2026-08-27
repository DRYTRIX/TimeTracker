import 'package:flutter/material.dart';

/// An item shown in a [SearchablePickerField].
class PickerItem<T> {
  final T value;
  final String title;
  final String? subtitle;

  const PickerItem({required this.value, required this.title, this.subtitle});
}

/// A form-field style searchable picker.
///
/// Renders like a `DropdownButtonFormField` (label + prefix icon) but opens a
/// searchable suggestion list, so every selection step looks and behaves the
/// same. When [onCreate] is provided and the typed text matches no item, a
/// 'Create "X"' row is offered at the top of the list.
class SearchablePickerField<T> extends StatefulWidget {
  final String label;
  final IconData icon;
  final List<PickerItem<T>> items;
  final PickerItem<T>? selected;
  final ValueChanged<PickerItem<T>>? onSelected;

  /// Called when the user taps the clear (x) button on a selected value.
  final VoidCallback? onClear;

  /// Called when the user types a name that matches no item.
  /// Returns the newly created item (or null on failure/abort).
  final Future<PickerItem<T>?> Function(String name)? onCreate;

  final bool enabled;
  final bool isLoading;
  final String? error;
  final VoidCallback? onRetry;
  final String searchHint;
  final String emptyText;

  const SearchablePickerField({
    super.key,
    required this.label,
    required this.icon,
    required this.items,
    required this.onSelected,
    this.selected,
    this.onClear,
    this.onCreate,
    this.enabled = true,
    this.isLoading = false,
    this.error,
    this.onRetry,
    this.searchHint = 'Search',
    this.emptyText = 'No matches',
  });

  @override
  State<SearchablePickerField<T>> createState() => _SearchablePickerFieldState<T>();
}

class _SearchablePickerFieldState<T> extends State<SearchablePickerField<T>> {
  final SearchController _searchController = SearchController();

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  List<PickerItem<T>> _matches(String query) {
    final q = query.trim().toLowerCase();
    if (q.isEmpty) return widget.items;
    return widget.items
        .where((i) =>
            i.title.toLowerCase().contains(q) ||
            (i.subtitle ?? '').toLowerCase().contains(q))
        .toList();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final hasSelection = widget.selected != null;

    return SearchAnchor(
      searchController: _searchController,
      viewHintText: widget.searchHint,
      builder: (context, controller) {
        return InkWell(
          onTap: widget.enabled ? controller.openView : null,
          borderRadius: BorderRadius.circular(12),
          child: InputDecorator(
            decoration: InputDecoration(
              labelText: widget.label,
              prefixIcon: Icon(widget.icon),
              suffixIcon: hasSelection && widget.enabled && widget.onClear != null
                  ? IconButton(
                      icon: const Icon(Icons.clear),
                      tooltip: 'Clear',
                      onPressed: () {
                        _searchController.clear();
                        widget.onClear!();
                      },
                    )
                  : (widget.isLoading
                      ? const SizedBox(
                          width: 20,
                          height: 20,
                          child: Padding(
                            padding: EdgeInsets.all(8),
                            child: CircularProgressIndicator(strokeWidth: 2),
                          ),
                        )
                      : widget.enabled
                          ? const Icon(Icons.arrow_drop_down)
                          : null),
              enabled: widget.enabled,
            ),
            child: Text(
              hasSelection ? widget.selected!.title : '',
              style: theme.textTheme.bodyLarge,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
          ),
        );
      },
      suggestionsBuilder: (context, controller) {
        final query = controller.text.trim();
        final matches = _matches(controller.text);

        if (widget.isLoading && widget.items.isEmpty) {
          return const [ListTile(title: Text('Loading...'))];
        }
        if (widget.error != null && widget.items.isEmpty) {
          return [
            ListTile(
              title: const Text('Could not load'),
              subtitle: Text(widget.error!),
              trailing: widget.onRetry != null
                  ? TextButton(onPressed: widget.onRetry, child: const Text('Retry'))
                  : null,
            ),
          ];
        }

        final suggestions = <Widget>[];

        if (widget.onCreate != null &&
            query.isNotEmpty &&
            matches.isEmpty) {
          suggestions.add(ListTile(
            leading: const Icon(Icons.add_circle_outline),
            title: Text('Create "$query"'),
            onTap: () async {
              controller.closeView('');
              final created = await widget.onCreate!(query);
              if (created != null) {
                widget.onSelected?.call(created);
              }
            },
          ));
        }

        if (matches.isEmpty && suggestions.isEmpty) {
          return [ListTile(title: Text(widget.emptyText))];
        }

        suggestions.addAll(matches.map((item) => ListTile(
              leading: CircleAvatar(
                child: Text(
                  (item.title.isNotEmpty ? item.title[0] : '?').toUpperCase(),
                  style: const TextStyle(fontWeight: FontWeight.w700),
                ),
              ),
              title: Text(item.title),
              subtitle:
                  (item.subtitle == null || item.subtitle!.isEmpty) ? null : Text(item.subtitle!),
              onTap: () {
                controller.closeView(item.title);
                widget.onSelected?.call(item);
              },
            )));

        return suggestions;
      },
    );
  }
}
