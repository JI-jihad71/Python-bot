
const DEFAULT_SOURCE =
  "https://ashtv.com.bd/server/iptv.m3u?v=1795545764097";

const CACHE_SECONDS = 60;

function json(data, status = 200) {
  return Response.json(data, {
    status,
    headers: {
      "Access-Control-Allow-Origin": "*",
      "Cache-Control": "public, s-maxage=60, stale-while-revalidate=120",
    },
  });
}

function parseAttributes(line) {
  const attrs = {};
  const regex = /([\w-]+)="([^"]*)"/g;
  let match;

  while ((match = regex.exec(line)) !== null) {
    attrs[match[1]] = match[2];
  }

  return attrs;
}

function parseM3U(content) {
  const lines = content.replace(/^\uFEFF/, "").split(/\r?\n/);
  const channels = [];

  let current = null;

  for (const raw of lines) {
    const line = raw.trim();

    if (!line) continue;

    if (line.startsWith("#EXTINF:")) {
      const comma = line.indexOf(",");
      const metadata = comma >= 0 ? line.slice(0, comma) : line;
      const name = comma >= 0 ? line.slice(comma + 1).trim() : "";

      const attrs = parseAttributes(metadata);

      current = {
        id: attrs["tvg-id"] || null,
        name,
        logo: attrs["tvg-logo"] || null,
        group: attrs["group-title"] || "Uncategorized",
        language: attrs["tvg-language"] || null,
        country: attrs["tvg-country"] || null,
        tvgName: attrs["tvg-name"] || null,
        streamUrl: null,
        attributes: attrs,
      };
    } else if (!line.startsWith("#") && current) {
      current.streamUrl = line;
      channels.push(current);
      current = null;
    }
  }

  return channels;
}

function createM3U(channels) {
  const output = ["#EXTM3U"];

  for (const channel of channels) {
    const attrs = channel.attributes || {};

    const metadata = Object.entries(attrs)
      .map(([key, value]) => `${key}="${String(value).replace(/"/g, "&quot;")}"`)
      .join(" ");

    output.push(
      `#EXTINF:-1 ${metadata},${channel.name}`
    );

    output.push(channel.streamUrl);
  }

  return output.join("\n") + "\n";
}

function filterChannels(channels, params) {
  const q = (params.get("q") || "").toLowerCase();
  const group = (params.get("group") || "").toLowerCase();

  return channels.filter(channel => {
    const searchText = [
      channel.name,
      channel.id,
      channel.group,
      channel.tvgName
    ].join(" ").toLowerCase();

    const matchesQuery = !q || searchText.includes(q);
    const matchesGroup =
      !group || channel.group.toLowerCase() === group;

    return matchesQuery && matchesGroup;
  });
}

export default async function handler(request) {
  if (request.method === "OPTIONS") {
    return new Response(null, {
      status: 204,
      headers: {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
      },
    });
  }

  if (request.method !== "GET") {
    return json({
      success: false,
      error: "Method not allowed",
    }, 405);
  }

  const url = new URL(request.url);
  const params = url.searchParams;
  const format = (params.get("format") || "m3u").toLowerCase();

  if (!["m3u", "m3u8", "json", "health"].includes(format)) {
    return json({
      success: false,
      error: "Unsupported format",
      supported: ["m3u", "m3u8", "json", "health"],
    }, 400);
  }

  if (format === "health") {
    return json({
      success: true,
      service: "IPTV Playlist API",
      status: "online",
      supportedFormats: ["m3u", "m3u8", "json"],
    });
  }

  try {
    const source = process.env.UPSTREAM_M3U_URL || DEFAULT_SOURCE;

    const upstream = await fetch(source, {
      method: "GET",
      headers: {
        "User-Agent": "Mozilla/5.0",
        "Accept": "*/*",
        "Referer": "https://ashtv.com.bd/",
      },
      signal: AbortSignal.timeout(15000),
      redirect: "follow",
    });

    if (!upstream.ok) {
      return json({
        success: false,
        error: "Upstream request failed",
        upstreamStatus: upstream.status,
      }, 502);
    }

    const content = await upstream.text();

    if (!content.trimStart().startsWith("#EXTM3U")) {
      return json({
        success: false,
        error: "Invalid M3U response",
      }, 502);
    }

    const channels = parseM3U(content);

    if (!channels.length) {
      return json({
        success: false,
        error: "No channels found",
      }, 502);
    }

    const filtered = filterChannels(channels, params);

    // M3U / M3U8 output
    if (format === "m3u" || format === "m3u8") {
      const playlist = createM3U(filtered);

      return new Response(playlist, {
        status: 200,
        headers: {
          "Content-Type": "application/vnd.apple.mpegurl; charset=utf-8",
          "Content-Disposition":
            `inline; filename="playlist.${format}"`,
          "Access-Control-Allow-Origin": "*",
          "Cache-Control":
            `public, s-maxage=${CACHE_SECONDS}, stale-while-revalidate=120`,
          "X-Playlist-Format": format,
          "X-Channel-Count": String(filtered.length),
        },
      });
    }

    // JSON pagination
    const offset = Math.max(
      0,
      parseInt(params.get("offset") || "0", 10) || 0
    );

    const requestedLimit = parseInt(
      params.get("limit") || "100",
      10
    );

    const limit = Math.min(
      500,
      Math.max(1, Number.isFinite(requestedLimit) ? requestedLimit : 100)
    );

    const items = filtered.slice(offset, offset + limit);

    const groups = [...new Set(
      channels.map(channel => channel.group)
    )];

    return json({
      success: true,
      api: "IPTV Playlist API",
      format: "json",
      total: filtered.length,
      totalSourceChannels: channels.length,
      offset,
      limit,
      hasMore: offset + limit < filtered.length,
      categories: groups,
      channels: items,
      generatedAt: new Date().toISOString(),
    });

  } catch (error) {
    return json({
      success: false,
      error: "Playlist service unavailable",
      message: error.name === "TimeoutError"
        ? "Upstream request timed out"
        : error.message,
    }, 502);
  }
}
