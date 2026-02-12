#ifndef WEB_UI_H
#define WEB_UI_H

#include <functional>
#include "app_types.h"

void setupWebUI(
  ControllerSettings& settings,
  AppState& state,
  const char* mdnsHostname,
  const std::function<void()>& onSettingsSaved
);
void handleWebUIClient();

#endif
