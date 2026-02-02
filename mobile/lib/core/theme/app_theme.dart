import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import 'app_tokens.dart';

/// TimeTracker brand colors aligned with the webapp (brand-colors.css / tailwind.config.js).
class AppColors {
  // Primary & secondary (webapp)
  static const Color primary = Color(0xFF4A90E2);
  static const Color primaryDark = Color(0xFF3B82F6);
  static const Color secondary = Color(0xFF50E3C2);
  static const Color secondaryDark = Color(0xFF06B6D4);

  // Light mode (webapp)
  static const Color bgLight = Color(0xFFF7F9FB);
  static const Color bgLightSecondary = Color(0xFFFFFFFF);
  static const Color textLight = Color(0xFF2D3748);
  static const Color textLightSecondary = Color(0xFFA0AEC0);
  static const Color textLightMuted = Color(0xFF718096);
  static const Color borderLight = Color(0xFFE2E8F0);

  // Dark mode (webapp)
  static const Color bgDark = Color(0xFF1A202C);
  static const Color bgDarkSecondary = Color(0xFF2D3748);
  static const Color textDark = Color(0xFFE2E8F0);
  static const Color textDarkSecondary = Color(0xFF718096);
  static const Color textDarkMuted = Color(0xFFA0AEC0);
  static const Color borderDark = Color(0xFF4A5568);

  // Status (webapp)
  static const Color success = Color(0xFF4CAF50);
  static const Color warning = Color(0xFFFF9800);
  static const Color error = Color(0xFFE53935);
  static const Color info = Color(0xFF2196F3);
}

class AppTheme {
  static TextTheme _textTheme({
    required Brightness brightness,
    required ColorScheme colorScheme,
  }) {
    final base = ThemeData(brightness: brightness, useMaterial3: true).textTheme;
    final themed = GoogleFonts.interTextTheme(base).apply(
      bodyColor: colorScheme.onSurface,
      displayColor: colorScheme.onSurface,
    );
    // Nudge key sizes/weights to feel more modern/consistent.
    return themed.copyWith(
      titleLarge: themed.titleLarge?.copyWith(fontWeight: FontWeight.w700),
      titleMedium: themed.titleMedium?.copyWith(fontWeight: FontWeight.w600),
      titleSmall: themed.titleSmall?.copyWith(fontWeight: FontWeight.w600),
      labelLarge: themed.labelLarge?.copyWith(fontWeight: FontWeight.w600),
    );
  }

  /// Light color scheme matching the webapp (brand-colors.css, tailwind).
  static ColorScheme get _lightColorScheme => ColorScheme.light(
        primary: AppColors.primary,
        onPrimary: Colors.white,
        primaryContainer: AppColors.primary.withValues(alpha: 0.2),
        onPrimaryContainer: AppColors.primary,
        secondary: AppColors.secondary,
        onSecondary: AppColors.textLight,
        secondaryContainer: AppColors.secondary.withValues(alpha: 0.3),
        onSecondaryContainer: AppColors.textLight,
        tertiary: AppColors.secondaryDark,
        onTertiary: Colors.white,
        tertiaryContainer: AppColors.secondaryDark.withValues(alpha: 0.25),
        onTertiaryContainer: AppColors.textLight,
        error: AppColors.error,
        onError: Colors.white,
        errorContainer: AppColors.error.withValues(alpha: 0.15),
        onErrorContainer: AppColors.error,
        surface: AppColors.bgLight,
        onSurface: AppColors.textLight,
        onSurfaceVariant: AppColors.textLightMuted,
        outline: AppColors.borderLight,
        outlineVariant: AppColors.borderLight.withValues(alpha: 0.6),
        surfaceContainerHighest: AppColors.bgLightSecondary,
        surfaceContainerLowest: AppColors.bgLightSecondary,
      );

  /// Dark color scheme matching the webapp dark mode.
  static ColorScheme get _darkColorScheme => ColorScheme.dark(
        primary: AppColors.primary,
        onPrimary: Colors.white,
        primaryContainer: AppColors.primary.withValues(alpha: 0.3),
        onPrimaryContainer: AppColors.textDark,
        secondary: AppColors.secondary,
        onSecondary: AppColors.textDark,
        secondaryContainer: AppColors.secondary.withValues(alpha: 0.25),
        onSecondaryContainer: AppColors.textDark,
        tertiary: AppColors.secondaryDark,
        onTertiary: Colors.white,
        tertiaryContainer: AppColors.secondaryDark.withValues(alpha: 0.3),
        onTertiaryContainer: AppColors.textDark,
        error: AppColors.error,
        onError: Colors.white,
        errorContainer: AppColors.error.withValues(alpha: 0.25),
        onErrorContainer: const Color(0xFFFCA5A5),
        surface: AppColors.bgDark,
        onSurface: AppColors.textDark,
        onSurfaceVariant: AppColors.textDarkSecondary,
        outline: AppColors.borderDark,
        outlineVariant: AppColors.borderDark.withValues(alpha: 0.6),
        surfaceContainerHighest: AppColors.bgDarkSecondary,
        surfaceContainerLowest: AppColors.bgDarkSecondary,
      );

  static ThemeData get lightTheme {
    final colorScheme = _lightColorScheme;
    return ThemeData(
      useMaterial3: true,
      colorScheme: colorScheme,
      textTheme: _textTheme(brightness: Brightness.light, colorScheme: colorScheme),
      scaffoldBackgroundColor: colorScheme.surface,
      appBarTheme: const AppBarTheme(
        centerTitle: true,
        elevation: 0,
      ),
      cardTheme: CardThemeData(
        elevation: 2,
        color: AppColors.bgLightSecondary,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppRadii.md),
        ),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(AppRadii.sm),
          ),
        ),
      ),
      floatingActionButtonTheme: FloatingActionButtonThemeData(
        backgroundColor: colorScheme.primary,
        foregroundColor: colorScheme.onPrimary,
        elevation: 2,
      ),
      navigationBarTheme: NavigationBarThemeData(
        backgroundColor: AppColors.bgLightSecondary,
        indicatorColor: colorScheme.primaryContainer,
        labelTextStyle: WidgetStateProperty.all(
          const TextStyle(fontSize: 12, fontWeight: FontWeight.w600),
        ),
        height: 72,
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: AppColors.bgLightSecondary,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppRadii.md),
        ),
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      ),
      dividerTheme: DividerThemeData(
        thickness: 1,
        space: 1,
        color: colorScheme.outlineVariant,
      ),
      chipTheme: ChipThemeData(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppRadii.lg)),
        side: BorderSide(color: colorScheme.outlineVariant),
        labelStyle: TextStyle(color: colorScheme.onSurface, fontWeight: FontWeight.w600),
      ),
      snackBarTheme: SnackBarThemeData(
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppRadii.sm),
        ),
        contentTextStyle: const TextStyle(fontSize: 14),
      ),
      dialogTheme: DialogThemeData(
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppRadii.lg),
        ),
        titleTextStyle: const TextStyle(
          fontSize: 20,
          fontWeight: FontWeight.w600,
        ),
      ),
      bottomSheetTheme: BottomSheetThemeData(
        showDragHandle: true,
        backgroundColor: AppColors.bgLightSecondary,
        modalBackgroundColor: AppColors.bgLightSecondary,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(AppRadii.xl)),
        ),
      ),
      listTileTheme: const ListTileThemeData(
        contentPadding: EdgeInsets.symmetric(horizontal: 16, vertical: 4),
        minLeadingWidth: 40,
      ),
    );
  }

  static ThemeData get darkTheme {
    final colorScheme = _darkColorScheme;
    return ThemeData(
      useMaterial3: true,
      colorScheme: colorScheme,
      textTheme: _textTheme(brightness: Brightness.dark, colorScheme: colorScheme),
      scaffoldBackgroundColor: colorScheme.surface,
      appBarTheme: const AppBarTheme(
        centerTitle: true,
        elevation: 0,
      ),
      cardTheme: CardThemeData(
        elevation: 2,
        color: AppColors.bgDarkSecondary,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppRadii.md),
        ),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(AppRadii.sm),
          ),
        ),
      ),
      floatingActionButtonTheme: const FloatingActionButtonThemeData(
        elevation: 2,
      ),
      navigationBarTheme: NavigationBarThemeData(
        backgroundColor: AppColors.bgDarkSecondary,
        indicatorColor: colorScheme.primaryContainer,
        labelTextStyle: WidgetStateProperty.all(
          const TextStyle(fontSize: 12, fontWeight: FontWeight.w600),
        ),
        height: 72,
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: AppColors.bgDarkSecondary,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppRadii.md),
        ),
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      ),
      dividerTheme: DividerThemeData(
        thickness: 1,
        space: 1,
        color: colorScheme.outlineVariant,
      ),
      chipTheme: ChipThemeData(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppRadii.lg)),
        side: BorderSide(color: colorScheme.outlineVariant),
        labelStyle: TextStyle(color: colorScheme.onSurface, fontWeight: FontWeight.w600),
      ),
      snackBarTheme: SnackBarThemeData(
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppRadii.sm),
        ),
        contentTextStyle: const TextStyle(fontSize: 14),
      ),
      dialogTheme: DialogThemeData(
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppRadii.lg),
        ),
        titleTextStyle: const TextStyle(
          fontSize: 20,
          fontWeight: FontWeight.w600,
        ),
      ),
      bottomSheetTheme: BottomSheetThemeData(
        showDragHandle: true,
        backgroundColor: AppColors.bgDarkSecondary,
        modalBackgroundColor: AppColors.bgDarkSecondary,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(AppRadii.xl)),
        ),
      ),
      listTileTheme: const ListTileThemeData(
        contentPadding: EdgeInsets.symmetric(horizontal: 16, vertical: 4),
        minLeadingWidth: 40,
      ),
    );
  }
}
