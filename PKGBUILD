# Maintainer: Lukash <lukash at aur dot archlinux dot org>
pkgname=dmtl-bin
pkgver=1.1.2
pkgrel=1
pkgdesc="Custom Linux launcher for DayZ"
arch=('x86_64')
url="https://github.com/69-Lukash/DMTLauncher"
license=('MIT')
provides=('dmtl')
conflicts=('dmtl')
source=("https://github.com/69-Lukash/DMTLauncher/releases/download/v${pkgver}/DMTL-Linux.tar.gz")
sha256sums=('SKIP')

package() {
    install -d "$pkgdir/opt/dmtl"
    cp -r "$srcdir/DMTL-Linux/"* "$pkgdir/opt/dmtl/"

    install -d "$pkgdir/usr/bin"
    ln -s /opt/dmtl/DMTL-Linux "$pkgdir/usr/bin/dmtl"
}
