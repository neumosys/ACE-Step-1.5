#include "PluginState.h"

namespace acestep::vst3
{
std::unique_ptr<juce::XmlElement> createStateXml(const PluginState& state)
{
    auto xml = std::make_unique<juce::XmlElement>(kStateRootTag);
    xml->setAttribute("schemaVersion", state.schemaVersion);
    xml->setAttribute("backendBaseUrl", state.backendBaseUrl);
    xml->setAttribute("sessionNote", state.sessionNote);
    return xml;
}

std::optional<PluginState> parseStateXml(const juce::XmlElement& xml)
{
    if (!xml.hasTagName(kStateRootTag))
    {
        return std::nullopt;
    }

    PluginState state;
    state.schemaVersion = xml.getIntAttribute("schemaVersion", kCurrentStateVersion);
    state.backendBaseUrl = xml.getStringAttribute("backendBaseUrl", kDefaultBackendBaseUrl).trim();
    state.sessionNote = xml.getStringAttribute("sessionNote").trim();

    if (state.backendBaseUrl.isEmpty())
    {
        state.backendBaseUrl = kDefaultBackendBaseUrl;
    }

    return state;
}
}  // namespace acestep::vst3
