#pragma once

#include <memory>
#include <optional>

#include <JuceHeader.h>

#include "PluginConfig.h"

namespace acestep::vst3
{
struct PluginState final
{
    int schemaVersion = kCurrentStateVersion;
    juce::String backendBaseUrl = kDefaultBackendBaseUrl;
    juce::String sessionNote;
};

[[nodiscard]] std::unique_ptr<juce::XmlElement> createStateXml(const PluginState& state);
[[nodiscard]] std::optional<PluginState> parseStateXml(const juce::XmlElement& xml);
}  // namespace acestep::vst3
